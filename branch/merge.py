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
    def __init__(self, source, target, projects, clear):
        super().__init__(utils, projects)
        self.end = None
        self.source = source
        self.target = target
        self.clear = clear
        self.filter()

    # 过滤项目
    def filter(self):
        for name in list(self.projects.keys()):
            project = self.projects.get(name)
            self.end = project.getEnd()
            branch_source = project.getBranch(self.source)
            if branch_source is None:
                self.projects.pop(name)
                continue
            branch_target = project.getBranch(self.target)
            if branch_target is None and self.end != self.backend:
                self.projects.pop(name)
                continue
            path = project.getPath()
            if path is None:
                self.projects.pop(name)
                continue

    def check_conflict(self):
        conflicts = []
        for p, p_info in self.projects.items():
            if self.is_trunk(self.target):
                continue
            if p_info.getBranch(self.target) is None:
                continue
            title = "test check conflicts"
            if self.end != self.backend and not p_info.checkConflicts(self.source, self.target, title):
                continue  # 非后端工程优先使用gitlab的冲突检查
            try:
                path = p_info.getPath()
                cmd = "cd {};git merge-base origin/{} origin/{}".format(path, self.source, self.target)
                [ret, base_sha] = subprocess.getstatusoutput(cmd)
                if ret != 0:
                    conflicts.append(p)
                    continue
                cmd = "cd {};git merge-tree {} origin/{} origin/{}".format(path, base_sha, self.source, self.target)
                [ret, merge_ret] = subprocess.getstatusoutput(cmd)
                if ret != 0 or "changed in both" in merge_ret:
                    conflicts.append(p)
                    continue
            except Exception as err:
                conflicts.append(p)
        return conflicts

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
            if path is None:
                continue
            if project.checkMerge(self.source, self.target):
                continue
            if self.is_trunk(self.target):
                option = "-X theirs -m 'Merge branch {} into {} & accept {}' origin/{}".format(self.source, self.target, self.source, self.source)
            else:
                option = "-m 'Merge branch {} into {}' origin/{} --no-ff".format(self.source, self.target, self.source)
            ret, merge_msg = subprocess.getstatusoutput('cd {};git merge {} --allow-unrelated-histories'.format(path, option))
            if ret != 0:
                _, abort_msg = subprocess.getstatusoutput('cd {};git merge --abort'.format(path))
                print("工程【{}】分支【{}】合并至分支【{}】失败【{}】".format(name, self.source, self.target, merge_msg))
                sys.exit(1)
            wait_push[name] = path
        self.push(wait_push)
        self.created(wait_created)
        self.tag()
        self.del_branch()

    def push(self, paths):
        if len(paths) < 1:
            return
        if self.end != self.backend:
            self.push_single(paths)
        else:
            self.push_batch(paths)

    # 单个工程push
    def push_single(self, paths):
        for k, v in paths.items():
            self.push_batch({k: v})

    # 批量push
    def push_batch(self, paths):
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
            print("工程【{}】从分支【{}】合并至【{}】成功".format(name, self.source, self.target))

    def tag(self):
        try:
            if not self.is_trunk(self.target):
                return True, str("目标分支非主干，无需打Tag")
            return True, self.create_tag()
        except Exception as err:
            return False, str(err)

    def create_tag(self):
        if self.end == self.backend:
            date = datetime.now().strftime("%Y%m%d%H%M")
            executor = CreateTag(self.target, date)
            executor.execute()
            return str("后端工程打Tag成功")
        date = datetime.now().strftime("%Y%m%d%H%M")
        for p_name, p_info in self.projects.items():
            if self.is_trunk(self.source):
                tag_name = "{}-{}".format(date, self.target)
            else:
                tag_name = self.source
            p_info.createTag(tag_name, self.target)
            print('工程【{}】分支【{}】打Tag【{}】成功'.format(p_name, self.target, tag_name))
        return str("前端工程打Tag成功")

    def created(self, projects):
        if len(projects) < 1:
            return
        if self.is_trunk(self.source):
            # 从主干分支合并至下游分支时，不创建分支
            return
        executor = CreateBranch(self.target, self.source, projects, True)
        executor.execute()

    # 删除工程模块分支
    def del_branch(self):
        if (self.source == "perform" and self.target == "master") or (self.clear and (not self.is_trunk(self.source))):
            delete_projects = self.projects.keys()
            executor = DeleteBranch(self.source, self.target, delete_projects, True)
            executor.execute()

    def execute(self):
        try:
            if len(self.projects) < 1:
                print("不存在待合并的工程!!!")
                sys.exit(1)
            self.checkout_branch(self.end, self.source)
            self.checkout_branch(self.end, self.target)
            conflict_projects = self.check_conflict()
            if len(conflict_projects) > 0:
                print("工程【{}】尝试从【{}】合并至【{}】请求发现冲突，需手动合并".format(",".join(conflict_projects), self.source, self.target))
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
        clear_source = ".clear" in sys.argv[1]
        source_branch = sys.argv[1].replace(".clear", "")
        target_branch = sys.argv[2]
        mr_projects = []
        if len(sys.argv) > 3:
            mr_projects = sys.argv[3:]
        Merge(source_branch, target_branch, mr_projects, clear_source).execute()
