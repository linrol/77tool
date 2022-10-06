# coding:utf-8
import sys
import utils
import subprocess
from common import Common
from createBranch import CreateBranch
from checkanddeleted import DeleteBranch

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
branch_group = {}


class Merge(Common):
    def __init__(self, source, target, clear):
        super().__init__(utils)
        self.source = source
        self.target = target
        self.clear = clear

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
        self.push(wait_push)
        self.created(wait_created)
        if not self.clear or self.source in ['stage', 'master']:
            return
        executor = DeleteBranch(self.source, self.target, None, True)
        executor.execute()

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

    def created(self, projects):
        if len(projects) < 1:
            return
        executor = CreateBranch(self.target, self.source, projects, True)
        executor.execute()

    def execute(self):
        try:
            self.checkout_branch(self.source)
            self.checkout_branch(self.target)
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


# 修改版本号
# 例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
# python3 merge.py sprint20220922 stage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: 输入参数错误, 正确的参数为：<source_branch> <target_branch>")
        sys.exit(1)
    else:
        clear_source = ".clear" in sys.argv[1]
        source_branch = sys.argv[1].replace(".clear", "")
        target_branch = sys.argv[2]
        Merge(source_branch, target_branch, clear_source).execute()
