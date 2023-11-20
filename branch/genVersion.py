# coding:utf-8
import sys
import getopt
import utils
import traceback
import requests
import uuid
import re
from common import Common
from datetime import datetime, timedelta


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
        self.project_names = self.filter_project(project_names)
        if self.fixed_version is None:
            self.target_date = target[-8:]
            self.target_name = target.replace(self.target_date, "")
            self.last_sprint, self.last_sprint_version = self.lookup_sprint_version(60, False)
            self.next_sprint, self.next_sprint_version = self.lookup_sprint_version(60, True)

    def is_feature(self):
        return self.fixed_version is not None

    def filter_project(self, names):
        result = set()
        if "framework" in names:    # 当平台工程首次创建时，才需要更新版本号
            result.add("framework")
        for name, p in self.projects.items():
            if name not in names and p.getModule() not in names:
                continue
            if p.getBranch(self.target) is None:
                continue
            if self.source_version.get(name) is None:
                continue
            if self.target_version.get(name) is None:
                continue
            result.add(name)
        return list(result)

    def lookup_sprint_version(self, days, is_forward):
        if self.target_name not in ["sprint", 'release']:
            return None, {}
        try:
            branches = self.project_build.getProject().branches
            sprint_list = list(map(lambda b: b.name, branches.list(search="^sprint20", all=True)))
            release_list = list(map(lambda b: b.name, branches.list(search="^release20", all=True)))
            branch_list = sprint_list + release_list
            for num in range(1, days):
                num = num if is_forward else -num
                for prefix in ['sprint', 'release']:
                    target_date = datetime.strptime(self.target_date, "%Y%m%d")
                    adjoin_date = target_date + timedelta(days=num)
                    name = prefix + adjoin_date.strftime("%Y%m%d")
                    if name not in branch_list:
                        continue
                    return name, self.get_branch_version(name)
            return None, {}
        except Exception as e:
            return None, {}

    def get_branch_offset(self, project_name):
        try:
            if self.source == "stage" and self.target_name == "release":
                # 判断release后的日期为周几-4，例：release20230710: 1-4 = -3
                num = datetime.strptime(self.target_date, "%Y%m%d").isoweekday()
                return num - 4
            offset = 0
            if self.target_name not in ["stage-patch", "perform-patch"]:
                return offset
            elif self.equals_version("master", self.target, project_name):
                offset += 1
                # 热更分支判断版本号和master一致时，偏移量+1
                if self.branch_is_presence("perform"):
                    if self.target_name == "stage-patch":
                        # 存在滚动分支且当前为stage-patch时，偏移量再+1
                        offset += 1
            return offset
        except Exception as e:
            print(str(e))
            traceback.print_exc()
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

    def gen_version(self, project_name):
        if self.is_feature():
            # 生成特性分支版本号
            return self.gen_feature_version(project_name)
        if self.target_name in ['sprint', 'release']:
            factory = self.factory_week()
        else:
            factory = self.factory_day()
        weight = self.get_branch_weight(self.source, self.target, project_name)
        if weight is None:
            raise Exception("工程【{}】分支【{}】获取权重值失败".format(project_name, self.target))
        inc_version = factory * weight
        source_version = self.source_version.get(project_name)
        target_version = self.target_version.get(project_name)
        if source_version is None:
            raise Exception("工程【{}】获取来源分支【{}】版本号失败".format(project_name, self.source))
        if target_version is None:
            raise Exception("工程【{}】获取目标分支【{}】版本号失败".format(project_name, self.target))
        source_prefix = source_version[0]
        target_prefix = target_version[0]
        source_min = source_version[1]
        target_min = target_version[1]
        if source_prefix != target_prefix:
            err_info = "{}({}),{}({})".format(self.source, source_prefix, self.target, target_prefix)
            print("工程【{}】来源和目标分支版本号前缀不一致【{}】".format(project_name, err_info))
            source_inc = int(source_min.replace("-SNAPSHOT", "")) + inc_version
            return "{}.{}-SNAPSHOT".format(source_prefix, source_inc)
        if "SNAPSHOT" in target_min and not self.force:
            print("工程【{}】目标分支【{}】已为快照版本【{}】".format(project_name, self.target, target_version))
            return None
        source_min = source_min.replace("-SNAPSHOT", "")
        target_min = target_min.replace("-SNAPSHOT", "")
        if not source_min.isdigit():
            err_info = "{}({}),{}({})".format(self.source, source_min, self.target, target_min)
            print("工程【{}】来源分支最小版本号非数字【{}】".format(project_name, err_info))
            return None
        source_min = int(source_min)
        # target_min = int(target_min)
        # 上一班车分支版本号+weight<=sprint增量的版本号需<=下一班车分支版本号+weight
        last_target_min = self.get_last_min_version(project_name, source_prefix, source_min)
        target_min = source_min + inc_version
        target_min = target_min + self.get_branch_offset(project_name)
        if last_target_min is None or self.source == "stage-global":
            ret = "{}.{}-SNAPSHOT".format(target_prefix, target_min)
            print("{}({}->{})".format(project_name, ".".join(source_version), ret))
            return ret
        if target_min < last_target_min + weight:
            target_min = last_target_min + weight
        ret = "{}.{}-SNAPSHOT".format(target_prefix, target_min)
        print("{}({}->{})".format(project_name, ".".join(source_version), ret))
        return ret

    def gen_feature_version(self, project_name):
        ver = self.source_version.get(project_name)
        if ver is None:
            return None
        prefix = re.match("[0-9]+[.][0-9]+", ver[0]).group()
        suffix = re.search(r"\b(\d+[.]\w+-SNAPSHOT)\b", self.fixed_version).group(1)
        return "{}.{}".format(prefix, suffix)

    def get_last_min_version(self, project_name, prefix, s_min):
        last_version = self.last_sprint_version.get(project_name, None)
        if last_version is None:
            return None
        adjacent_prefix = last_version[0]
        if prefix != adjacent_prefix:
            return None
        last_min = last_version[1].replace("-SNAPSHOT", "")
        if not last_min.isdigit():
            return None
        if int(last_min) <= int(s_min):
            return None
        return int(last_min)

    # 矫正下个班车版本号
    def correct_version(self, project_versions):
        try:
            if self.is_feature():
                return
            if self.next_sprint is None:
                return
            ret = ""
            for project, version in project_versions.items():
                version = version.rsplit(".", 1)
                next_version = self.next_sprint_version.get(project)
                if next_version is None:
                    continue
                if not self.project_branch_is_presence(project, self.next_sprint):
                    continue
                next_prefix = next_version[0]
                next_min = next_version[1].replace("-SNAPSHOT", "")
                this_prefix = version[0]
                this_min = version[1].replace("-SNAPSHOT", "")
                if this_prefix != next_prefix:
                    continue
                if not next_min.isdigit() or not this_min.isdigit():
                    continue
                weight = self.get_branch_weight(self.source, self.target, project)
                if int(next_min) > int(this_min):
                    continue
                correct_version = "{}.{}-SNAPSHOT".format(next_prefix, int(this_min) + weight)
                ret += ("," if len(ret) > 0 else '') + project + ":" + correct_version
            if len(ret) > 0:
                url = "https://branch.linrol.cn/branch/correct"
                correct_id = ''.join(str(uuid.uuid4()).split('-'))
                user_id = self.get_gl_user_name()
                params = "?correct_id={}&user_id={}&branch={}&project={}".format(correct_id, user_id, self.next_sprint, ret)
                requests.get(url + params)
        except Exception as e:
            print(e)
            return

    def execute(self):
        try:
            gen_version = {}
            for project_name in self.project_names:
                version = self.gen_version(project_name)
                if version is None:
                    continue
                gen_version[project_name] = version
            self.update_build_version(self.target, gen_version)
            self.correct_version(gen_version)
            return gen_version
        except Exception as e:
            print(str(e))
            traceback.print_exc()
            sys.exit(1)


# 生成版本号
if __name__ == "__main__":
    try:
        arg_str = ["help", "force", "version=", "source=", "target=", "project="]
        opts, args = getopt.getopt(sys.argv[1:], "hfv:s:t:p:", arg_str)
        opts_dict = dict(opts)
        force_update = not opts_dict.keys().isdisjoint({"-f", "--force"})
        source_branch = opts_dict.get("-s", opts_dict.get("-source"))
        target_branch = opts_dict.get("-t", opts_dict.get("-target"))
        fixed_version = opts_dict.get("-v", opts_dict.get("-version", None))
        projects = opts_dict.get("-p", opts_dict.get("-project")).split(",")
        GenVersion(force_update, fixed_version, source_branch, target_branch, projects).execute()
    except getopt.GetoptError as err:
        print(err)
        traceback.print_exc()
        usage()
        sys.exit(1)
