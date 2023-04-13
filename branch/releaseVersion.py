# coding:utf-8
import sys
import utils
from common import Common

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
branch_group = {}
module_mapping = {"all": ['framework', 'enterprise', 'enterprise-apps', 'enterprise-apps-api', 'global-apps', 'global-apps-api'],
                  "global": ['framework', 'global-apps', 'global-apps-api'],
                  "apps": ['framework', 'enterprise', 'enterprise-apps', 'enterprise-apps-api']
                  }


class ReleaseVersion(Common):
    def __init__(self, source, target, category):
        super().__init__(utils)
        self.source = source
        self.target = target
        self.category = category
        self.source_version = self.get_branch_version(source)
        self.target_version = self.get_branch_version(target, True)
        self.target_date = target[-8:]
        self.target_name = target.replace(self.target_date, "")

    def execute(self):
        try:
            replace_version = {}
            for gp in list(self.category.keys()):
                if len(self.category.get(gp)) < 1:
                    continue
                pv = self.category.pop(gp, {})
                for p, v in pv.items():
                    replace_version[p] = v
                    print("工程【{}】自身版本修改为【{}】".format(p, v))

            for k, v in self.target_version.items():
                name = self.branch_group.get(k)
                if name not in self.category.keys():
                    continue
                if k in replace_version:
                    continue
                prefix = v[0]
                min_version = v[1].replace("-SNAPSHOT", "")
                replace_version[k] = "{}.{}".format(prefix, min_version)
            if len(replace_version) < 1:
                print("工程【所有模块】的分支【{}】已为发布版本号".format(self.target))
                sys.exit(1)
            if not self.check_front_version_release(replace_version):
                print("ERROR:前端预制目前是快照版本，请联系前端值班提供Release版本后重试")
                sys.exit(1)
            self.update_build_version(self.target, replace_version)
            return replace_version
        except Exception as err:
            print(str(err))
            sys.exit(1)

    # 检查前端预制数据是否为发布包版本号
    def check_front_version_release(self, replace_version):
        if "reimburse" in replace_version:
            return True
        if module not in module_mapping.keys():
            return True
        if module in ["global"]:
            return True
        front_version = self.target_version.get("reimburse")
        if front_version is None:
            return True
        for v in front_version:
            if "SNAPSHOT" in v:
                return False
        return True


# 修改版本号
# 例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
# python3 releaseVersion.py stage sprint20220818 all/global/apps other=budget:2.1;budget-api:2.2;project:2.3;framework:2.4
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("ERROR: 输入参数错误, 正确的参数为：<source_branch> <target_branch> <module> <other=budget:2.1>")
        sys.exit(1)
    else:
        source_branch = sys.argv[1]
        target_branch = sys.argv[2]
        module = sys.argv[3]
        mapping = {}

        if module in module_mapping.keys():
            categories = module_mapping.get(module)
            for i in categories:
                mapping[i] = {}

        for pg in sys.argv[4:]:
            gv = pg.split("=")
            g = gv[0]
            mapping[g] = dict(i.split(":") for i in gv[1].split(","))
        ReleaseVersion(source_branch, target_branch, mapping).execute()
