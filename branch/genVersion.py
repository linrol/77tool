# coding:utf-8
import os
import sys

import utils
import re
import yaml
import ruamel.yaml
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"

branch_weight = {"emergency": 1, "stage-patch": 1, "sprint": 7}
project_convert = ["app-build-plugins", "app-common", "baseapp-api",
                   "common-base", "common-base-api", "graphql-api",
                   "graphql-impl", "json-schema-plugin", "mbg-plugins",
                   "metadata-api", "metadata-impl", "sql-parser"]
branch_group = {}


class GenVersion:
    def __init__(self, source, target, force, project_names):
        self.source = source
        self.target = target
        self.force = force
        self.project_names, self.projects = self.pre_process(project_names)
        self.project_build = self.projects.get('build')
        self.source_version = self.get_branch_version(source)
        self.target_version = self.get_branch_version(target)
        pattern = r"([a-zA-Z-]+|[20]\d{7})"
        self.target_name, self.target_date = re.findall(pattern, target)
        self.last_target_version = self.get_last_branch_version()
        self.pool = ThreadPoolExecutor(max_workers=10)

    def pre_process(self, project_names):
        result = set()
        for name in project_names:
            if name in project_convert:
                name = "framework"
            result.add(name)
        return list(result), utils.project_path(set.union(result, {"build"}))

        # 根据工程名称获取指定分支的远程文件

    def get_project_branch_file(self, project, branch_name, file_path):
        f = project.getProject().files.get(file_path=file_path, ref=branch_name)
        if f is None:
            raise Exception(
                "工程【{}】分支【{}】不存在文件【{}】".format(project, branch_name, file_path))
        config_yaml = yaml.load(f.decode(), Loader=yaml.FullLoader)
        return config_yaml

    def write_build_version(self, branch_name, project_versions):
        self.project_build.checkout(branch_name)
        config_yaml_path = os.path.join(os.curdir,
                                        '../../apps/build/config.yaml').replace(
            "\\", "/")
        yaml = ruamel.yaml.YAML()
        config = yaml.load(open(config_yaml_path))
        for project, version in project_versions.items():
            group = branch_group.get(project)
            config[group][project] = version
        with open(config_yaml_path, 'w') as f:
            yaml.dump(config, f)

    # 获取指定分支的版本号
    def get_branch_version(self, branch):
        if self.project_build is None:
            raise Exception("工程【build】未找到，请检查git是否存在该项目")
        project_build_branch = self.project_build.getBranch(branch)
        if project_build_branch is None:
            raise Exception("工程【build】不存在分支【{}】".format(branch))
        config_yaml = self.get_project_branch_file(self.project_build, branch,
                                                   'config.yaml')
        branch_version = {}
        for group, item in config_yaml.items():
            if type(item) is dict:
                for k, v in item.items():
                    branch_group[k] = group
                    branch_version[k] = v.rsplit(".", 1)
        if len(branch_version) < 1:
            raise Exception("根据分支【{}】获取工程版本号失败".format(branch))
        return branch_version

    def get_last_branch_version(self):
        if self.target_name != "sprint":
            return {}
        target_date = datetime.strptime(self.target_date, "%Y%m%d")
        last_week_date = target_date + timedelta(days=-7)
        last_branch = self.target_name + last_week_date.strftime("%Y%m%d")
        try:
            return self.get_branch_version(last_branch)
        except Exception as e:
            return {}

    def factory_day(self):
        date_target = datetime.strptime(self.target_date + "235959",
                                        "%Y%m%d%H%M%S")
        return (date_target - datetime.today()).days + 1

    def factory_week(self):
        # week_start = datetime.strptime(start_time, '%Y%m%d')
        week_start = datetime.today()
        week_end = datetime.strptime(self.target_date, '%Y%m%d')
        year_week_num = 52
        week_end_year = week_end.year
        week_start_year = week_start.year
        week_end_num = int(datetime.strftime(week_end, "%W"))
        week_start_num = int(datetime.strftime(week_start, "%W"))
        return (
                   week_end_year - week_start_year) * year_week_num + week_end_num - week_start_num

    def get_emergency_branch(self):
        try:
            emergency_branch_name = "emergency" + self.target_date
            return self.get_branch_version(emergency_branch_name)
        except Exception as e:
            return None

    def get_replace_version(self, factory, project_name):
        weight = branch_weight.get(self.target_name)
        inc_version = factory * weight
        source_version = self.source_version.get(project_name)
        target_version = self.target_version.get(project_name)
        if source_version is None:
            raise Exception(
                "工程【{}】获取来源分支【{}】版本号失败".format(project_name, self.source))
        source_prefix = source_version[0]
        target_prefix = target_version[0]
        if source_prefix != target_prefix:
            err_info = "{}({}),{}({})".format(self.source, source_prefix,
                                              self.target, target_prefix)
            print("工程【{}】来源和目标分支版本号前缀不一致【{}】".format(project_name, err_info))
            return None
        source_min = source_version[1]
        target_min = target_version[1]
        if "SNAPSHOT" in target_min and not self.force:
            print("工程【{}】目标分支【{}】已为快照版本【{}】".format(project_name, self.target,
                                                    target_version))
            return None
        source_min = source_min.replace("-SNAPSHOT", "")
        target_min = target_min.replace("-SNAPSHOT", "")
        if not (source_min.isdigit() and target_min.isdigit()):
            err_info = "{}({}),{}({})".format(self.source, source_min,
                                              self.target, target_min)
            print("工程【{}】来源和目标分支最小版本号非数字【{}】".format(project_name, err_info))
        target_min = str(int(source_min) + inc_version)
        ret_version = "{}.{}-SNAPSHOT".format(target_prefix, target_min)
        # sprint增量的版本号需>=上一班车分支版本号+weight
        last_target_version = self.last_target_version.get(project_name, None)
        if last_target_version is None:
            return ret_version
        last_target_prefix = last_target_version[0]
        if source_prefix != last_target_prefix:
            return ret_version
        last_target_min = last_target_version[1].replace("-SNAPSHOT", "")
        if not last_target_min.isdigit():
            return ret_version
        if int(last_target_min) <= int(source_min):
            return ret_version
        if int(source_min) + int(inc_version) - int(last_target_min) >= weight:
            return ret_version
        target_min = int(last_target_min) + weight
        return "{}.{}-SNAPSHOT".format(target_prefix, target_min)

    def execute(self):
        if self.target_name in ['sprint']:
            factory = self.factory_week()
        else:
            factory = self.factory_day()
        replace_version = {}
        for project_name in self.project_names:
            version = self.get_replace_version(factory, project_name)
            if version is None:
                continue
            replace_version[project_name] = version
        self.write_build_version(self.target, replace_version)
        return replace_version


# 修改版本号
# 例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
# python3 changeVersion.py hotfix true
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "ERROR: 输入参数错误, 正确的参数为：<source_branch> <target_branch> [project...]")
        sys.exit(1)
    elif len(sys.argv) < 4:
        print(
            "ERROR: 输入参数错误, 正确的参数为：<source_branch> <target_branch> [project...]")
    else:
        source_branch = sys.argv[1]
        force = ".force" in sys.argv[2]
        target_branch = sys.argv[2].replace(".force", "")
        GenVersion(source_branch, target_branch, force, sys.argv[3:]).execute()
