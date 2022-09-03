import os
import yaml
import ruamel.yaml


def get_project_branch_file(project, branch_name, file_path):
    f = project.getProject().files.get(file_path=file_path, ref=branch_name)
    if f is None:
        raise Exception(
            "工程【{}】分支【{}】不存在文件【{}】".format(project, branch_name,
                                                    file_path))
    config_yaml = yaml.load(f.decode(), Loader=yaml.FullLoader)
    return config_yaml


class Common:
    def __init__(self, utils):
        self.branch_group = {}
        self.utils = utils
        self.projects = utils.project_path()
        self.project_build = self.projects.get('build')

    # 获取指定分支的版本号
    def get_branch_version(self, branch, skip_release=False):
        if self.project_build is None:
            raise Exception("工程【build】未找到，请检查git是否存在该项目")
        project_build_branch = self.project_build.getBranch(branch)
        if project_build_branch is None:
            raise Exception("工程【build】不存在分支【{}】".format(branch))
        config_yaml = get_project_branch_file(self.project_build, branch,
                                                   'config.yaml')
        branch_version = {}
        for group, item in config_yaml.items():
            if type(item) is dict:
                for k, v in item.items():
                    if skip_release and "SNAPSHOT" not in v:
                        continue
                    self.branch_group[k] = group
                    branch_version[k] = v.rsplit(".", 1)
        # if len(branch_version) < 1:
            # print("根据分支【{}】获取工程版本号失败".format(branch))
            # raise Exception("根据分支【{}】获取工程版本号失败".format(branch))
        return branch_version

    # 更新版本号
    def update_build_version(self, branch_name, project_versions):
        self.project_build.checkout(branch_name)
        path = '../../apps/build/config.yaml'
        config_path = os.path.join(os.curdir, path).replace("\\", "/")
        ruamel_yaml = ruamel.yaml.YAML()
        config = ruamel_yaml.load(open(config_path))
        for project, version in project_versions.items():
            group = self.branch_group.get(project)
            config[group][project] = version
        with open(config_path, 'w') as f:
            ruamel_yaml.dump(config, f)
