import os
import sys
import redis
import subprocess
from request import post_form
from log import logger
sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/data/backend/branch-manage")
from branch import utils


class Common:
    def __init__(self):
        self.utils = utils
        self.projects = utils.project_path()
        self.project_build = self.projects.get('build')
        self.project_init_data = self.projects.get('init-data')
        self.redis_pool = redis.ConnectionPool(host="linrol.cn", port=6379,
                                               password='linrol_redis', db=2,
                                               decode_responses=True,
                                               max_connections=16)

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
    def checkout_branch(self, branch_name):
        cmd = 'cd ../branch;python3 checkout.py {}'.format(branch_name)
        return self.exec(cmd, True, False)

    # 删除分支
    def clear_branch(self, branch_name):
        try:
            cmd = 'cd ../branch;python3 checkanddeleted.py {} none'.format(branch_name)
            return self.exec(cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 保护分支
    def protect_branch(self, branch, protect):
        try:
            protect_cmd = "cd ../branch;python3 protectBranch.py {} {}".format(branch, protect)
            return self.exec(protect_cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 触发ops编译
    def ops_build(self, branch, skip=False):
        try:
            build_url = "http://ops.q7link.com:8000/qqdeploy/projectbuild/"
            if skip:
                return
            post_form(build_url, {"branch": branch, "byCaller": "值班助手"})
        except Exception as e:
            logger.error(e)


