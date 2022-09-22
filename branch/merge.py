# coding:utf-8
import sys
import utils
import subprocess
from common import Common

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
branch_group = {}


class Merge(Common):
    def __init__(self, source, target):
        super().__init__(utils)
        self.source = source
        self.target = target

    def check_conflict(self):
        conflict_project = []
        for p, p_info in self.projects.items():
            branch = p_info.getBranch(self.source)
            if branch is None:
                continue
            path = p_info.getPath()
            cmd = "cd {};git merge-base {} {}".format(path, self.source, self.target)
            [ret, base_sha] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                conflict_project.append(p)
                continue
            cmd = "cd {};git merge-tree {} {} {}".format(path, base_sha, self.source, self.target)
            [ret, merge_ret] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                conflict_project.append(p)
                continue
            if "changed in both" in merge_ret:
                conflict_project.append(p)
                continue
        return conflict_project

    def merge(self):
        pass

    def execute(self):
        try:
            conflict_projects = self.check_conflict()
            if len(conflict_projects) > 0:
                print("工程【{}】尝试合并请求发现冲突，放弃分支合并".format(",".join(conflict_projects)))
                sys.exit(1)
            print("enjoy, no conflict")
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
        source_branch = sys.argv[1]
        target_branch = sys.argv[2]
        Merge(source_branch, target_branch).execute()
