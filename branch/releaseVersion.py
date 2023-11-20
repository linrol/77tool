# coding:utf-8
import sys
import traceback

import utils
from common import Common

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
branch_group = {}
module_mapping = {
    "all": ['framework', 'enterprise', 'enterprise-apps', 'enterprise-apps-api', 'global-apps', 'global-apps-api'],
    "global": ['framework', 'global-apps', 'global-apps-api'],
    "apps": ['framework', 'enterprise', 'enterprise-apps', 'enterprise-apps-api']
}


class ReleaseVersion(Common):
    def __init__(self, target, category):
        super().__init__(utils)
        self.target = target
        self.category = category
        self.target_date = target[-8:]
        self.target_name = target.replace(self.target_date, "")

    # 构建正式包
    def build(self):
        try:
            version = self.get_branch_version(self.target, True)
            if len(version) < 1:
                print("工程【All】分支【{}】已为发布版本号".format(self.target))
                sys.exit(1)
            replace = {}
            for gp in list(self.category.keys()):
                if len(self.category.get(gp)) < 1:
                    continue
                pv = self.category.pop(gp, {})
                for p, v in pv.items():
                    replace[p] = v
                    print("工程【{}】自身版本修改为【{}】".format(p, v))
            # 替换-SNAPSHOT为空串
            for k, v in version.items():
                name = self.branch_group.get(k)
                if name not in self.category.keys():
                    continue
                if k in replace:
                    continue
                prefix = v[0]
                replace[k] = "{}.{}".format(prefix, v[1].replace("-SNAPSHOT", ""))
            if len(replace) < 1:
                print("分支【{}】没有需要待构建的快照包版本".format(self.target))
                sys.exit(1)
            if not self.check_front_version_release(replace, version.get("reimburse")):
                print("ERROR:前端预制目前是快照版本，请联系前端值班提供Release版本后重试")
                sys.exit(1)
            self.update_build_version(self.target, replace)
            return replace
        except Exception as err:
            print(str(err))
            sys.exit(1)

    # 检查前端预制数据是否为发布包版本号
    @staticmethod
    def check_front_version_release(replace_version, front_version):
        if "reimburse" in replace_version:
            return True
        if module not in module_mapping.keys():
            return True
        if module in ["global"]:
            return True
        if front_version is None:
            return True
        for v in front_version:
            if "SNAPSHOT" in v:
                return False
        return True

    # 回退正式包并删除仓库的jar包
    def destroy(self):
        try:
            replace = {}
            version = self.get_branch_version(self.target, False)
            for name, p in self.projects.items():
                if p.getBranch(self.target) is None:
                    continue
                name_alias = "framework" if p.getModule() == "platform" else name
                v = version.get(name_alias)
                if v is None:
                    continue
                if "SNAPSHOT" in v[1]:
                    continue
                jar_version = "{}.{}".format(v[0], v[1])
                self.maven_delete(name, jar_version)
                if "api" in name:
                    self.maven_delete("{}-private".format(name), jar_version)
                else:
                    self.maven_delete("{}-gen".format(name), jar_version)
                if "parent" == name:
                    self.maven_delete("app-parent", jar_version)
                    self.maven_delete("app-api-parent", jar_version)
                replace[name_alias] = "{}-SNAPSHOT".format(jar_version)
            if len(replace) < 1:
                print("分支【{}】没有需要回退的发布包版本".format(self.target))
                sys.exit(1)
            self.update_build_version(self.target, replace)
            return replace
        except Exception as err:
            traceback.print_exc()
            sys.exit(1)


# 修改版本号
# 例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
# python3 releaseVersion.py build/destroy sprint20220818 all/global/apps other=budget:2.1,budget-api:2.2,project:2.3,framework:2.4
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("ERROR: 输入参数错误, 正确的参数为：<action> <target_branch> <module> <other=budget:2.1>")
        sys.exit(1)
    else:
        action = sys.argv[1]
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
        release = ReleaseVersion(target_branch, mapping)
        getattr(release, action)()
