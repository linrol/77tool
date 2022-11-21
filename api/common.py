import os
import sys
import subprocess
from base import Base
from log import logger
sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/data/backend/branch-manage")
from branch import utils
date_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'


class Common(Base):
    def __init__(self):
        self.chdir_branch()
        self.utils = utils
        self.front_projects = utils.project_path(["front"])
        self.projects = {**utils.project_path(), **self.front_projects}
        self.project_build = self.projects.get('build')
        self.project_init_data = self.projects.get('init-data')

    def exec(self, command, throw=False, level_info=True):
        [ret, msg] = subprocess.getstatusoutput(command)
        if throw and ret != 0:
            logger.error("exec[{}] ret[{}]".format(command, msg))
            raise Exception(str(msg))
        if level_info:
            logger.info("exec[{}] ret[{}]".format(command, msg))
        return [ret == 0, msg]

    def chdir_branch(self):
        os.chdir("../branch/")

    def chdir_data_pre(self):
        os.chdir("../dataPre/")

    # 是否首次创建分支
    def init_create_branch(self, branch):
        return self.project_build.getBranch(branch) is None

    # 获取清空build脚本的参数
    def get_clear_build_params(self, branch):
        if self.init_create_branch(branch):
            return "true"
        else:
            return "false"

    # 切换本地分支
    def checkout_branch(self, branch, end="backend"):
        cmd = 'cd ../branch;python3 checkout.py {} {}'.format(end, branch)
        return self.exec(cmd, True, False)

    # 删除分支
    def clear_branch(self, branch):
        try:
            cmd = 'cd ../branch;python3 checkanddeleted.py {} none'.format(branch)
            return self.exec(cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 保护分支
    def protect_branch(self, branch, protect, projects=None):
        try:
            protect_cmd = "cd ../branch;python3 protectBranch.py {} {}".format(branch, protect)
            if projects is not None:
                protect_cmd += " {}".format(" ".join(projects))
            return self.exec(protect_cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 获取合并代码的分支
    def get_merge_branch(self, branches, clusters, is_backend):
        duty_branches = self.get_duty_branches()
        branch_merge = {}
        for branch in branches:
            if self.is_chinese(branch):
                continue
            branch_prefix, _ = self.get_branch_date(branch)
            if len(duty_branches) > 0 and branch_prefix not in duty_branches:
                continue
            if is_backend and "sprint" in branch and "集群0" in clusters:
                branch = "stage-global"
            if is_backend and self.project_build.getBranch(branch) is None:
                continue
            target = self.get_branch_created_source(branch)
            if target is None:
                continue
            if is_backend and self.project_build.getBranch(target) is None:
                continue
            branch_merge[branch] = target
        if len(branch_merge) < 1:
            raise Exception("解析合并分支信息失败")
        if len(branch_merge) > 1:
            raise Exception("解析合并分支信息不唯一: {}".format(branch_merge))
        for k, v in branch_merge.items():
            return k, v



