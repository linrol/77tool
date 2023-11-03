import os
import ruamel.yaml
import redis
import subprocess
import requests
import json
NEXUS_URL = 'http://nexus.q7link.com:8081'
auth = ('branch-ci', 'branch-ci')


class Node(object):
    def __init__(self, data, next_node=None):
        self.branch = data.get('branch')
        self.version = data.get('version')
        self.next = next_node

    def before_next(self):
        if self.next is None:
            return False
        prefix = self.version[0].split(".")
        next_prefix = self.next.version[0].split(".")
        if len(prefix) != len(next_prefix):
            return False
        for i, next_i in zip(prefix, next_prefix):
            if not i.isdigit() or not next_i.isdigit():
                return False
            if int(i) == int(next_i):
                continue
            return int(i) < int(next_i)
        last = self.version[1].replace("-SNAPSHOT", "")
        next_last = self.next.version[1].replace("-SNAPSHOT", "")
        if not last.isdigit() or not next_last.isdigit():
            return False
        return int(last) <= int(next_last)

    def __str__(self):
        return "{}({}.{})".format(self.branch, self.version[0], self.version[1])

    def inc_next_version(self, inc):
        next_prefix = self.next.version[0]
        next_last = self.next.version[1].replace("-SNAPSHOT", "")
        inc_next_last = str(int(next_last) + inc)
        return next_prefix + "." + self.next.version[1].replace(next_last,
                                                                inc_next_last)


class LinkedList(object):
    def __init__(self, head=None):
        self.head = head

    def __len__(self):
        curr_node = self.head
        counter = 0
        while curr_node is not None:
            counter += 1
            curr_node = curr_node.next
        return counter

    # 在链表前面插入节点
    def insert(self, data):
        if data is None:
            return None
        # 原来的头结点 , 是新头节点的next
        node = Node(data, self.head)
        self.head = node
        return node

    # 从链表后面插入节点
    def append(self, data):
        if data is None:
            return None
        node = Node(data)
        if self.head is None:
            self.head = node
            return node
        # 从头节点开始寻找当前链表尾指针
        curr_node = self.head
        while curr_node.next is not None:
            curr_node = curr_node.next
        # 链表尾指针指向新插入的node
        curr_node.next = node
        return node


class Common:
    backend = "backend"

    def __init__(self, utils, projects=None, readonly_redis=True):
        self.branch_group = {}
        self.utils = utils
        self.projects = utils.init_projects(projects)
        self.project_build = self.projects.get('build')
        self.port = 6378 if readonly_redis else 6379
        self.password = "readonly" if readonly_redis else os.environ.get("REDIS_PASSWORD")
        self.redis_pool = redis.ConnectionPool(host="linrol.cn",
                                               port=self.port,
                                               password=self.password, db=2,
                                               decode_responses=True,
                                               max_connections=16)
        self.weights = self.hgetall("q7link-branch-weight")

    def __del__(self):
        self.get_connection().close()

    def get_connection(self):
        return redis.Redis(connection_pool=self.redis_pool)

    def hgetall(self, name):
        return self.get_connection().hgetall(name)

    def hget(self, name, key):
        return self.get_connection().hget(name, key)

    def hset(self, name, key, value):
        self.get_connection().hset(name, key, value)

    def get_gl_user_name(self):
        ps = list(self.projects.values())
        if len(ps) < 1:
            return None
        return ps[0].getGl().user.username

    # 获取指定分支的版本号
    def get_branch_version(self, branch, skip_release=False):
        if self.project_build is None:
            raise Exception("工程【build】未找到，请检查git是否存在该项目")
        build_branch = self.project_build.getBranch(branch)
        if build_branch is None:
            raise Exception("工程【build】不存在分支【{}】".format(branch))
        yaml_parse = self.utils.yaml_parse
        config_yaml = self.utils.get_project_file(self.project_build, branch, 'config.yaml', yaml_parse)
        version = {}
        for group, item in config_yaml.items():
            if type(item) is not dict:
                continue
            for k, v in item.items():
                self.branch_group[k] = group
                if group in ["cache"]:
                    continue
                if skip_release and "SNAPSHOT" not in v:
                    continue
                version[k] = v.rsplit(".", 1)
        return version

    # 更新版本号
    def update_build_version(self, branch_name, project_versions):
        if len(project_versions) < 1:
            return
        self.project_build.checkout(branch_name)
        path = '../../apps/build/config.yaml'
        config_path = os.path.join(os.curdir, path).replace("\\", "/")
        ruamel_yaml = ruamel.yaml.YAML()
        config = ruamel_yaml.load(open(config_path))
        for project, version in project_versions.items():
            group = self.branch_group.get(project)
            version = int(version) if version.isdigit() else version
            config[group][project] = version
        with open(config_path, 'w') as f:
            ruamel_yaml.dump(config, f)

    # 检查分支是否存在
    def branch_is_presence(self, branch_name):
        for p_info in self.projects.values():
            branch = p_info.getBranch(branch_name)
            if branch is None:
                continue
            return True
        return False

    # 检查指定工程的分支是否存在
    def project_branch_is_presence(self, project, branch_name):
        p_info = self.projects.get(project)
        if p_info is None:
            return False
        return p_info.getBranch(branch_name) is not None

    # 判断是否为主干分支
    def is_trunk(self, branch):
        return branch in ['stage', 'perform', 'master']

    # 切换本地分支
    def checkout_branch(self, end, branch_name):
        cmd = 'cd ../branch;python3 checkout.py {} {}'.format(end, branch_name)
        return subprocess.getstatusoutput(cmd)

    # 版本号比较
    def equals_version(self, b1, b2, p):
        vs1 = self.get_branch_version(b1).get(p)
        vs2 = self.get_branch_version(b2).get(p)
        if vs1 is None or vs2 is None:
            return False
        if len(vs1) != len(vs2):
            return False
        for v1, v2 in zip(vs1, vs2):
            if v1 != v2:
                return False
        return True

    # 判断版本号是否为布包版
    def is_release(self, versions):
        for v in versions:
            if "SNAPSHOT" not in v:
                continue
            return False
        return True

    # 获取分支权重
    def get_branch_weight(self, source, target, project):
        target_date = target[-8:]
        target_name = target.replace(target_date, "")
        key = "{}_{}_{}".format(source, target_name, project)
        weight = self.weights.get(key)
        if weight is not None:
            return int(weight)
        key1 = "{}_{}_*".format(source, target_name)
        weight = self.weights.get(key1)
        if weight is not None:
            return int(weight)
        key2 = "*_{}_*".format(target_name)
        weight = self.weights.get(key2)
        return int(weight)

    @staticmethod
    def nexus_search(repository, group_id, artifact_id, version):
        search_url = "{}/service/rest/v1/search?repository={}&maven.groupId={}&maven.artifactId={}&maven.extension=jar&version={}".format(NEXUS_URL, repository, group_id, artifact_id, version)
        headers = {'content-type': 'application/json', 'charset': 'utf-8'}
        response = requests.get(search_url, auth=auth, headers=headers)
        data = json.loads(response.content.decode())
        print(data)
        return data

    @staticmethod
    def nexus_delete(module_id):
        delete_url = "{}/service/rest/v1/components/{}".format(NEXUS_URL, module_id)
        headers = {'content-type': 'application/json', 'charset': 'utf-8'}
        print(delete_url)
        response = requests.delete(delete_url, auth=auth, headers=headers)
        return response.status_code == 204

    def nexus_delete(self, repository, group_id, artifact_id, version):
        ret = self.nexus_search(repository, group_id, artifact_id, version)
        items = ret.get('items')
        if len(items) != 1:
            print("not found jar")
        else:
            item_id = items[0].get("id")
            ret = self.nexus_delete(item_id)
            print("delete ret {}".format(ret))

