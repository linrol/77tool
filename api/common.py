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
    def checkout_branch(self, branch):
        cmd = 'cd ../branch;python3 checkout.py {}'.format(branch)
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



