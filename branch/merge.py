# coding:utf-8
import sys
import utils
import subprocess
from datetime import datetime
from common import Common
from createBranch import CreateBranch
from checkanddeleted import DeleteBranch
from tag import CreateTag

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
branch_group = {}


class Merge(Common):
    def __init__(self, end, source, target, includes, clear):
        super().__init__(utils, end)
        self.includes = includes
        self.filter_projects()
        self.source = source
        self.target = target
        self.clear = clear

    # 过滤项目
    def filter_projects(self):
        if self.includes is None or len(self.includes) < 1:
            return
        for k in list(self.projects.keys()):
            if k not in self.includes:
                self.projects.pop(k)

    def check_conflict(self):
        conflict_project = []
        for p, p_info in self.projects.items():
            branch_source = p_info.getBranch(self.source)
            if branch_source is None:
                continue
            branch_target = p_info.getBranch(self.target)
            if branch_target is None:
                continue
            path = p_info.getPath()
            cmd = "cd {};git merge-base origin/{} origin/{}".format(path, self.source, self.target)
            [ret, base_sha] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                conflict_project.append(p)
                continue
            cmd = "cd {};git merge-tree {} origin/{} origin/{}".format(path, base_sha, self.source, self.target)
            [ret, merge_ret] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                conflict_project.append(p)
                continue
            if "changed in both" in merge_ret:
                conflict_project.append(p)
                continue
        return conflict_project

    def merge(self):
        wait_created = []
        wait_push = {}
        for name, project in self.projects.items():
            branch_source = project.getBranch(self.source)
            branch_target = project.getBranch(self.target)
            if branch_source is None:
                continue
            if branch_target is None:
                wait_created.append(name)
                continue
            path = project.getPath()
            ret, merge_msg = subprocess.getstatusoutput('cd {};git merge origin/{}'.format(path, self.source))
            if ret != 0:
                _, abort_msg = subprocess.getstatusoutput('cd {};git merge --abort'.format(path))
                print("工程【{}】分支【{}】合并至分支【{}】失败【{}】".format(name, self.source, self.target, merge_msg))
                sys.exit(1)
            wait_push[name] = path
        self.push_end(wait_push)
        self.created(wait_created)
        self.tag()
        if not self.clear or self.source in ['stage', 'master']:
            return
        delete_projects = None
        if self.is_front:
            delete_projects = self.projects.keys()
        executor = DeleteBranch(self.source, self.target, delete_projects, True)
        executor.execute()

    def push_end(self, paths):
        if not self.is_front:
            self.push(paths)
        else:
            for k, v in paths.items():
                self.push({k: v})

    def push(self, paths):
        cmd = ''
        for path in paths.values():
            cmd += ';cd ' + path + ';git push origin {}'.format(self.target)
        if len(cmd) < 1:
            return
        [ret, msg] = subprocess.getstatusoutput(cmd.replace(';', '', 1))
        if ret != 0:
            print("push error:{}".format(msg))
            sys.exit(1)
        for name in paths.keys():
            print("工程【{}】分支【{}】合并至【{}】成功".format(name, self.source, self.target))

    def tag(self):
        try:
            if self.target not in ["stage", "master"]:
                return True, str("ignore")
            date = datetime.now().strftime("%Y%m%d%H%M")
            if self.is_front:
                return True, self.create_front_tag()
            executor = CreateTag(self.target, date)
            executor.execute()
            return True, str("success")
        except Exception as err:
            return False, str(err)

    def create_front_tag(self):
        date = datetime.now().strftime("%Y%m%d")
        for p_name, p_info in self.projects.items():
            tag = p_info.getLastTag()
            if tag is None:
                continue
            tag_str = tag.name.split(".")
            if not tag_str[2].isdigit():
                continue
            tag_prefix = "{}.{}.".format(tag_str[0], tag_str[1])
            tag_num = tag_str[2]
            tag_name = tag_prefix + "{}.{}-{}".format(int(tag_num) + 1, date,
                                                      self.target)
            p_info.createTag(tag_name, self.target)
            print('工程【{}】分支【{}】打Tag【{}】成功'.format(p_name, self.target,
                                                         tag_name))
        return str("success")

    def created(self, projects):
        if len(projects) < 1:
            return
        executor = CreateBranch(self.target, self.source, projects, True)
        executor.execute()

    def execute(self):
        try:
            self.checkout_branch(self.source, self.includes)
            self.checkout_branch(self.target, self.includes)
            conflict_projects = self.check_conflict()
            if len(conflict_projects) > 0:
                print("工程【{}】尝试合并请求发现冲突，需手动合并".format(",".join(conflict_projects)))
                sys.exit(1)
            self.merge()
            for project in self.projects.values():
                project.deleteLocalBranch(self.source)
        except Exception as err:
            print(str(err))
            sys.exit(1)


# 代码合并
# 例：将sprint20220922分支代码合并至stage
# python3 merge.py sprint20220922 stage
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("ERROR: 输入参数错误, 正确的参数为：<end> <source_branch> <target_branch>")
        sys.exit(1)
    else:
        belong_end = sys.argv[1]
        clear_source = ".clear" in sys.argv[2]
        source_branch = sys.argv[2].replace(".clear", "")
        target_branch = sys.argv[3]
        mr_projects = []
        if len(sys.argv) > 4:
            mr_projects = sys.argv[4:]
        Merge(belong_end, source_branch, target_branch, mr_projects, clear_source).execute()
