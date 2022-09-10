# coding:utf-8
import sys
import utils
from common import Common

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
branch_group = {}


class ReleaseVersion(Common):
    def __init__(self, source, target, group):
        super().__init__(utils)
        self.source = source
        self.target = target
        self.group = group
        self.source_version = self.get_branch_version(source)
        self.target_version = self.get_branch_version(target, True)
        self.target_date = target[-8:]
        self.target_name = target.replace(self.target_date, "")

    def execute(self):
        try:
            replace_version = {}
            for k, v in self.target_version.items():
                gn = self.branch_group.get(k)
                if gn not in self.group.keys():
                    continue
                gkv = self.group.get(gn).get(k)
                if gkv is not None:
                    replace_version[k] = gkv
                    continue
                if k == "reimburse":
                    continue
                prefix = v[0]
                min_version = v[1].replace("-SNAPSHOT", "")
                replace_version[k] = "{}.{}".format(prefix, min_version)
            if len(replace_version) < 1:
                print("工程【所有模块】的分支【{}】已为发布版本号".format(self.target))
                sys.exit(1)
            self.update_build_version(self.target, replace_version)
            return replace_version
        except Exception as err:
            print(str(err))
            sys.exit(1)


# 修改版本号
# 例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
# python3 changeVersion.py hotfix true
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("ERROR: 输入参数错误, 正确的参数为：<source_branch> <target_branch> <group>")
        sys.exit(1)
    else:
        source_branch = sys.argv[1]
        target_branch = sys.argv[2]
        project_group = {}
        for pg in sys.argv[3:]:
            gv = pg.split(":")
            g = gv[0]
            if len(gv) < 2:
                project_group[g] = {}
                continue
            project_group[g] = dict(i.split("=") for i in gv[1].split(";"))
        ReleaseVersion(source_branch, target_branch, project_group).execute()
