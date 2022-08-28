# coding:utf-8
import os
import re
import sys

import ruamel.yaml
import yaml

import utils

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
branch_group = {}


class ReleaseVersion:
    def __init__(self, source, target):
        self.source = source
        self.target = target
        self.project_build = utils.project_path({"build"}).get('build')
        self.source_version = self.get_branch_version(source)
        self.target_version = self.get_branch_version(target)
        pattern = r"([a-zA-Z-]+|[20]\d{7})"
        self.target_name, self.target_date = re.findall(pattern, target)

    def get_project_branch_file(self, project, branch_name, file_path):
        f = project.getProject().files.get(file_path=file_path, ref=branch_name)
        if f is None:
            raise Exception(
                "工程【{}】分支【{}】不存在文件【{}】".format(project, branch_name,
                                                        file_path))
        config_yaml = yaml.load(f.decode(), Loader=yaml.FullLoader)
        return config_yaml

    def write_build_version(self, branch_name, project_versions):
        self.project_build.checkout(branch_name)
        path = '../../apps/build/config.yaml'
        config_yaml_path = os.path.join(os.curdir, path).replace("\\", "/")
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

    def execute(self):
        try:
            replace_version = {}
            for k, v in self.target_version.items():
                if k == "reimburse":
                    continue
                prefix = v[0]
                min_version = v[1]
                if "-SNAPSHOT" not in min_version:
                    continue
                min_version = min_version.replace("-SNAPSHOT", "")
                replace_version[k] = "{}.{}".format(prefix, min_version)
            if len(replace_version) < 1:
                print("工程【所有模块】的分支【{}】已为发布版本号".format(self.target))
                sys.exit(1)
            self.write_build_version(self.target, replace_version)
            return replace_version
        except Exception as err:
            print(str(err))
            sys.exit(1)


# 修改版本号
# 例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
# python3 changeVersion.py hotfix true
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("ERROR: 输入参数错误, 正确的参数为：<source_branch> <target_branch>")
        sys.exit(1)
    else:
        source_branch = sys.argv[1]
        target_branch = sys.argv[2]
        ReleaseVersion(source_branch, target_branch).execute()
