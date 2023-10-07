import os
import sys
import subprocess
import yaml
import gitlab
from datetime import datetime, timedelta
from base import Base
from log import logger
sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/data/backend/branch-manage")
from branch import utils


class Common(Base):
    def __init__(self):
        self.chdir_branch()
        self.utils = utils
        self.projects = utils.init_projects([self.backend, self.front, self.other])
        self.project_build = self.projects.get('build')
        self.project_init_data = self.projects.get('init-data')

    @staticmethod
    def exec(command, throw=False, level_info=True):
        [ret, msg] = subprocess.getstatusoutput(command)
        if throw and ret != 0:
            logger.error("exec[{}] ret[{}]".format(command, msg))
            raise Exception(str(msg))
        if level_info:
            logger.info("exec[{}] ret[{}]".format(command, msg))
        return [ret == 0, msg]

    @staticmethod
    def chdir_branch():
        os.chdir("../branch/")

    @staticmethod
    def chdir_data_pre():
        os.chdir("../dataPre/")

    # 判断项目分支是否存在
    def branch_is_present(self, project, branch):
        return self.projects.get(project).getBranch(branch) is not None

    # 获取清空build脚本的参数
    def get_clear_build_params(self, branch):
        return "false" if self.branch_is_present("build", branch) else "true"

    # 切换本地分支
    def checkout_branch(self, branch, end="backend"):
        cmd = 'cd ../branch;python3 checkout.py {} {}'.format(end, branch)
        return self.exec(cmd, True, False)

    # 删除远程分支
    def clear_branch(self, branch, projects=""):
        try:
            cmd = 'cd ../branch;python3 checkanddeleted.py {} none {}'.format(branch, projects)
            return self.exec(cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 获取远端文件
    @staticmethod
    def git_file(project, branch, file_path):
        try:
            return project.getProject().files.get(file_path=file_path, ref=branch)
        except gitlab.exceptions.GitlabGetError:
            return None

    # 创建分支
    def create_branch(self, projects, source, target):
        msg = ""
        for name in projects:
            project = self.projects.get(name)
            if project is None:
                continue
            if project.getBranch(target) is not None:
                continue
            real_source = project.createBranch(source, target)
            msg += "工程【{}】基于分支【{}】创建分支【{}】成功\n".format(name, real_source, target)
        return True, msg

    # 清空前端升级脚本
    def clear_front_upgrade(self, projects, branch, path):
        try:
            name = "front-goserver"
            if name not in projects:
                raise Exception("当前工程不涉及升级接口文件")
            project = self.projects.get(name)
            file = self.git_file(project, branch, path)
            if file is None:
                raise Exception("升级接口文件不存在")
            message = "{}-task-0000-{}".format(branch, "清空升级接口")
            file.content = ''
            file.save(branch=branch, commit_message=message)
            return True, "工程【{}】清空升级接口【{}】成功\n".format(name, path)
        except Exception as err:
            logger.error(str(err))
            return False, ""

    # 保护分支
    def protect_branch(self, branch, protect, projects=None):
        if projects is None:
            projects = []
        elif "all" in projects:
            projects.extend(["apps", "global", "platform"])
            projects.remove("all")
        elif "apps" in projects:
            projects.extend(["platform", "init-data"])
        elif "global" in projects:
            projects.extend(["platform", "init-data"])
        try:
            cmd = "cd ../branch;python3 protectBranch.py {} {} {}".format(branch, protect, " ".join(projects))
            return self.exec(cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 保护分支(直接调用git)
    def protect_git_branch(self, branch, project, access):
        try:
            tmp_msg = ""
            if access == "hotfix":
                mr_access = utils.MAINTAINER_ACCESS
                push_access = utils.VISIBILITY_PRIVATE
                tmp_msg = "取消"
            elif access == "none":
                mr_access = utils.VISIBILITY_PRIVATE
                push_access = utils.VISIBILITY_PRIVATE
            else:
                raise Exception("分支保护不支持的权限参数")
            _p_list = self.projects.get("parent").getGl().projects.list(search=project, min_access_level=40)
            _p = None
            for temp in _p_list:
                if temp.name == project:
                    _p = temp
                    break
            if _p is None:
                raise Exception("工程【】在gitlab未找到".format(project))
            _protect_list = _p.protectedbranches
            try:
                _p_b = _protect_list.get(branch).delete()
            except Exception as err:
                logger.warn(err)
            _protect_list.create({
                'name': branch,
                'merge_access_level': mr_access,
                'push_access_level': push_access
            })
            return True, "工程【{}】分支【{}】{}保护成功".format(project, branch, tmp_msg)
        except Exception as err:
            logger.exception(err)
            return False, str(err)

    # 获取指定分支的版本号
    def get_branch_version(self, branch):
        config_yaml = self.get_build_config(branch)
        version = {}
        for group, item in config_yaml.items():
            if type(item) is not dict:
                continue
            for k, v in item.items():
                self.project_category[k] = group
                if group in ["cache"]:
                    continue
                version[k] = v
        if len(version) < 1:
            raise Exception("根据分支【{}】获取工程版本号失败".format(branch))
        return version

    # 根据工程名称获取指定分支的远程文件
    def get_build_config(self, branch_name):
        build_branch = self.project_build.getBranch(branch_name)
        if build_branch is None:
            raise Exception("工程【build】不存在分支【{}】".format(branch_name))
        file = self.git_file(self.project_build, branch_name, "config.yaml")
        if file is None:
            raise Exception("工程【build】分支【{}】不存在文件【config.yaml】".format(branch_name))
        config_yaml = yaml.load(file.decode(), Loader=yaml.FullLoader)
        return config_yaml

    # 分支版本号比较，用于判断两个分支代码是否一致
    def equals_version(self, left, right):
        left_version = self.get_branch_version(left)
        right_version = self.get_branch_version(right)
        if left_version is None or right_version is None:
            return False
        return left_version == right_version

    # 获取项目涉及的模块
    def get_project_module(self, projects):
        ret = set()
        for p in projects:
            p_info = self.projects.get(p)
            if p_info is None:
                continue
            ret.add(p_info.getModule())
        return list(ret)

    def get_branch_creator(self, target):
        creator = None
        feature_info = self.get_branch_feature(target)
        if feature_info is not None:
            creator = feature_info.split("@")[2]
            return creator
        one_year = (datetime.utcnow() - timedelta(days=360)).isoformat()
        i = 0
        events = self.project_build.getProject().events.list(action='pushed', page=i, per_page=100, after=one_year)
        while len(events) > 0 and creator is None:
            for e in events:
                if e.action_name != 'pushed new':
                    continue
                branch = e.push_data.get('ref')
                if branch is None:
                    continue
                if branch != target:
                    continue
                creator = e.author_username
                if creator is not None:
                    break
            i += 1
            events = self.project_build.getProject().events.list(action='pushed', page=i, per_page=100, after=one_year)
        return self.userid2name(creator)
