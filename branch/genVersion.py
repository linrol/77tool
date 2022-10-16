# coding:utf-8
import sys
import getopt
import utils
from common import Common
from checkVersion import CheckVersion
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

project_framework = ["app-build-plugins", "app-common", "baseapp-api",
                     "common-base", "common-base-api", "graphql-api",
                     "graphql-impl", "json-schema-plugin", "mbg-plugins",
                     "metadata-api", "metadata-impl", "sql-parser"]


def usage():
    print('''
    -h --help show help info
    -f --force update version
    -s --source update from branch version
    -t --target update to branch version
    -p --project gen project list
    ''')
    sys.exit(1)
    pass



class GenVersion(Common):
    def __init__(self, force, version, source, target, project_names):
        super().__init__(utils)
        self.force = force
        self.fixed_version = version
        self.source = source
        self.target = target
        self.project_names = self.project_convert(project_names)
        self.source_version = self.get_branch_version(source)
        if self.fixed_version is None:
            self.target_version = self.get_branch_version(target)
            self.target_date = target[-8:]
            self.target_name = target.replace(self.target_date, "")
            self.weight = self.get_branch_weight()
            self.last_target_version = self.get_adjacent_branch_version(-7)
            self.next_target_version = self.get_adjacent_branch_version(7)

    def project_convert(self, project_names):
        result = set()
        for name in project_names:
            if name in project_framework:
                name = "framework"
            result.add(name)
        if self.force:
            compare_dict = {self.target: True, self.source: False}
            force_project = CheckVersion().compare_version(compare_dict, False)
            if len(force_project) > 0:
                result.update(force_project)
        return list(result)

    def get_branch_weight(self):
        key = "{}_{}".format(self.source, self.target_name)
        weight = self.hget("q7link-branch-weight", key)
        if weight is not None:
            return int(weight)
        key = "{}_{}".format("*", self.target_name)
        weight = self.hget("q7link-branch-weight", key)
        return int(weight)

    def get_adjacent_branch_version(self, days):
        if self.target_name != "sprint":
            return {}
        target_date = datetime.strptime(self.target_date, "%Y%m%d")
        last_week_date = target_date + timedelta(days=days)
        last_branch = self.target_name + last_week_date.strftime("%Y%m%d")
        try:
            return self.get_branch_version(last_branch)
        except Exception as err:
            print(str(err))
            return {}

    def get_branch_offset(self, project_name, target_prefix, target_min):
        if self.target_name != "stage-patch":
            return 0
        try:
            offset_branch = "emergency" + self.target_date
            offset_version = self.get_branch_version(offset_branch, True)
            if project_name not in offset_version.keys():
                return 0
            opv = offset_version.get(project_name)
            if target_prefix != opv[0]:
                return 0
            opv_min = int(opv[1].replace("-SNAPSHOT", ""))
            if target_min > opv_min:
                return 0
            return opv_min - target_min + 1
        except Exception as e:
            print(str(e))
            return 0

    def factory_day(self):
        target_date_full = self.target_date + "235959"
        date_target = datetime.strptime(target_date_full, "%Y%m%d%H%M%S")
        return (date_target - datetime.today()).days + 1

    def factory_week(self):
        week_start = datetime.today()
        week_end = datetime.strptime(self.target_date, '%Y%m%d')
        year_week_num = 52
        week_end_year = week_end.year
        week_start_year = week_start.year
        week_end_num = int(datetime.strftime(week_end, "%W"))
        week_start_num = int(datetime.strftime(week_start, "%W"))
        week_sub = week_end_num - week_start_num + 1
        return (week_end_year - week_start_year) * year_week_num + week_sub

    def get_replace_version(self, project_name):
        if self.target_name in ['sprint']:
            factory = self.factory_week()
        else:
            factory = self.factory_day()
        if self.weight is None:
            raise Exception("工程【{}】分支【{}】获取权重值失败".format(project_name,
                                                                  self.target))
        inc_version = factory * self.weight
        source_version = self.source_version.get(project_name)
        target_version = self.target_version.get(project_name)
        if source_version is None:
            raise Exception(
                "工程【{}】获取来源分支【{}】版本号失败".format(project_name,
                                                            self.source))
        source_prefix = source_version[0]
        target_prefix = target_version[0]
        source_min = source_version[1]
        target_min = target_version[1]
        if source_prefix != target_prefix:
            err_info = "{}({}),{}({})".format(self.source, source_prefix,
                                              self.target, target_prefix)
            print("工程【{}】来源和目标分支版本号前缀不一致【{}】".format(
                project_name, err_info))
            source_inc = int(source_min.replace("-SNAPSHOT", "")) + inc_version
            return "{}.{}-SNAPSHOT".format(source_prefix, source_inc)
        if "SNAPSHOT" in target_min and not self.force:
            print("工程【{}】目标分支【{}】已为快照版本【{}】".format(project_name,
                                                                self.target,
                                                                target_version))
            return None
        source_min = source_min.replace("-SNAPSHOT", "")
        target_min = target_min.replace("-SNAPSHOT", "")
        if not (source_min.isdigit() and target_min.isdigit()):
            err_info = "{}({}),{}({})".format(self.source, source_min,
                                              self.target, target_min)
            print("工程【{}】来源和目标分支最小版本号非数字【{}】".format(
                project_name, err_info))
            return None
        source_min = int(source_min)
        # target_min = int(target_min)
        # 上一班车分支版本号+weight<=sprint增量的版本号需<=下一班车分支版本号+weight
        last_target_min = self.get_adjacent_min_version(project_name,
                                                        source_prefix,
                                                        source_min, True)
        next_target_min = self.get_adjacent_min_version(project_name,
                                                        source_prefix,
                                                        source_min, False)
        target_min = source_min + inc_version
        offset = self.get_branch_offset(project_name, target_prefix, target_min)
        target_min = target_min + offset
        if last_target_min is None and next_target_min is None:
            return "{}.{}-SNAPSHOT".format(target_prefix, target_min)
        if last_target_min is not None and next_target_min is not None:
            inc_version = (next_target_min - last_target_min) // 2
            target_min = last_target_min + inc_version
        if next_target_min is not None:
            inc_version = (next_target_min - source_min) // 2
            target_min = source_min + inc_version
        if last_target_min is not None:
            less_weight = source_min + inc_version - last_target_min < self.weight
            target_min = last_target_min + self.weight if less_weight else target_min
        if target_min - source_min < 2:
            target_min = source_min + self.weight
            print("工程【{}】目标分支【{}】增量版本号小于2请确认下个班车版本号".
                  format(project_name, self.target))
        return "{}.{}-SNAPSHOT".format(target_prefix, target_min)

    def get_adjacent_min_version(self, project_name, prefix, s_min, is_last):
        if is_last:
            adjacent_version = self.last_target_version.get(project_name, None)
        else:
            adjacent_version = self.next_target_version.get(project_name, None)
        if adjacent_version is None:
            return None
        adjacent_prefix = adjacent_version[0]
        if prefix != adjacent_prefix:
            return None
        adjacent_min = adjacent_version[1].replace("-SNAPSHOT", "")
        if not adjacent_min.isdigit():
            return None
        if int(adjacent_min) <= int(s_min):
            return None
        return int(adjacent_min)

    def execute(self):
        try:
            replace_version = {}
            for project_name in self.project_names:
                if self.fixed_version is not None:
                    replace_version[project_name] = self.fixed_version
                    continue
                version = self.get_replace_version(project_name)
                if version is None:
                    continue
                replace_version[project_name] = version
            self.update_build_version(self.target, replace_version)
            return replace_version
        except Exception as e:
            print(str(e))
            sys.exit(1)


# 生成版本号
if __name__ == "__main__":
    try:
        arg_str = ["help", "force", "source=", "target=", "weight=", "project="]
        opts, args = getopt.getopt(sys.argv[1:], "hfv:s:t:p:", arg_str)
        opts_dict = dict(opts)
        force_update = not opts_dict.keys().isdisjoint({"-f", "--force"})
        source_branch = opts_dict.get("-s", opts_dict.get("-source"))
        target_branch = opts_dict.get("-t", opts_dict.get("-target"))
        fixed_version = opts_dict.get("-v", opts_dict.get("-fixed_version",
                                                          None))
        projects = opts_dict.get("-p", opts_dict.get("-project")).split(",")
        GenVersion(force_update, fixed_version, source_branch, target_branch,
                   projects).execute()
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(1)
