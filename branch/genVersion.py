# coding:utf-8
import sys
import getopt
import utils
import traceback
from common import Common
from checkVersion import CheckVersion
from datetime import datetime, timedelta

project_platform = ["app-build-plugins", "app-common", "app-common-api",
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
        self.source_version = self.get_branch_version(source)
        self.target_version = self.get_branch_version(target)
        self.project_names = self.project_convert(project_names)
        if self.fixed_version is None:
            self.target_date = target[-8:]
            self.target_name = target.replace(self.target_date, "")
            self.last_target_version = self.get_adjacent_branch_version(-7)
            self.next_target_version = self.get_adjacent_branch_version(7)

    def project_convert(self, project_names):
        result = set()
        for name in project_names:
            is_platform = name in project_platform
            if is_platform:
                name = "framework"
                if self.fixed_version is not None:
                    fsv = self.source_version.get(name)
                    is_same = self.equals_version(self.target, self.source, name)
                    if not self.is_release(fsv) and not is_same:
                        # 当目标工程为快照版本号且和来源版本号不形同时，则无需更新版本号
                        continue
            result.add(name)
        if self.force and self.source not in ["stage-global"]:
            compare_dict = {self.target: True, self.source: False}
            force_project = CheckVersion().compare_version(compare_dict, False)
            if len(force_project) > 0:
                result.update(force_project)
        return list(result)

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

    def get_branch_offset(self, project_name):
        if self.target_name not in ["stage-patch", "release"]:
            return 0
        try:
            if self.target_name == "release":
                return -1
            elif self.equals_version(self.source, self.target, project_name):
                return 1
            return 0
        except Exception as e:
            print(str(e))
            return 0

    def factory_day(self):
        target_date_full = self.target_date + "235959"
        date_target = datetime.strptime(target_date_full, "%Y%m%d%H%M%S")
        factory = (date_target - datetime.today()).days + 1
        if factory < 1:
            return 1
        return factory

    def factory_week(self):
        week_start = datetime.today()
        week_end = datetime.strptime(self.target_date, '%Y%m%d')
        year_week_num = 52
        week_end_year = week_end.year
        week_start_year = week_start.year
        week_end_num = int(datetime.strftime(week_end, "%W"))
        week_start_num = int(datetime.strftime(week_start, "%W"))
        week_sub = week_end_num - week_start_num + 1
        factory = (week_end_year - week_start_year) * year_week_num + week_sub
        if factory < 1:
            return 1
        return factory

    def get_replace_version(self, project_name):
        if self.target_name in ['sprint', 'release']:
            factory = self.factory_week()
        else:
            factory = self.factory_day()
        weight = self.get_branch_weight(self.source, self.target, project_name)
        if weight is None:
            raise Exception("工程【{}】分支【{}】获取权重值失败".format(project_name,
                                                                  self.target))
        inc_version = factory * weight
        source_version = self.source_version.get(project_name)
        target_version = self.target_version.get(project_name)
        if source_version is None:
            raise Exception(
                "工程【{}】获取来源分支【{}】版本号失败".format(project_name,
                                                            self.source))
        if target_version is None:
            raise Exception(
                "工程【{}】获取目标分支【{}】版本号失败".format(project_name,
                                                            self.target))
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
        target_min = target_min + self.get_branch_offset(project_name)
        if last_target_min is None and next_target_min is None:
            ret = "{}.{}-SNAPSHOT".format(target_prefix, target_min)
            print("{}({}->{})".format(project_name, ".".join(source_version), ret))
            return ret
        if self.source == "stage-global":
            ret = "{}.{}-SNAPSHOT".format(target_prefix, target_min)
            print("{}({}->{})".format(project_name, ".".join(source_version), ret))
            return ret
        if last_target_min is not None and next_target_min is not None:
            inc_version = (next_target_min - last_target_min) // 2
            target_min = last_target_min + inc_version
        if next_target_min is not None:
            inc_version = (next_target_min - source_min) // 2
            target_min = source_min + inc_version
        if last_target_min is not None:
            less_weight = source_min + inc_version - last_target_min < weight
            target_min = last_target_min + weight if less_weight else target_min
        if target_min - source_min < 2:
            target_min = source_min + weight
            print("工程【{}】目标分支【{}】增量版本号小于2请确认下个班车版本号".
                  format(project_name, self.target))
        ret = "{}.{}-SNAPSHOT".format(target_prefix, target_min)
        print("{}({}->{})".format(project_name, ".".join(source_version), ret))
        return ret

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
                    source_version = self.source_version.get(project_name)
                    if source_version is None:
                        raise Exception("look {} version by config.yaml[{}] not fount".format(project_name, self.source))
                    version = "{}.{}".format(source_version[0], self.fixed_version[4:])
                    replace_version[project_name] = version
                    continue
                version = self.get_replace_version(project_name)
                if version is None:
                    continue
                replace_version[project_name] = version
            self.update_build_version(self.target, replace_version)
            return replace_version
        except Exception as e:
            traceback.print_exc()
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