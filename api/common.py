import os
import sys
import subprocess
import re
from request import post_form, get
from log import logger
from redisclient import get_branch_mapping, hget
sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/data/backend/branch-manage")
from branch import utils
date_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'


class Common:
    def __init__(self):
        self.chdir_branch()
        self.utils = utils
        self.projects = utils.project_path()
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
    def protect_branch(self, branch, protect, projects=None):
        try:
            protect_cmd = "cd ../branch;python3 protectBranch.py {} {}".format(branch, protect)
            if projects is not None:
                protect_cmd += " {}".format(" ".join(projects))
            return self.exec(protect_cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 获取分支前缀和时间
    def get_branch_date(self, branch):
        if re.search(date_regex, branch):
            date = re.search(date_regex, branch).group()
            name = branch.replace(date, "")
            return name, date
        return branch, None

    # 获取值班人
    def get_duty_info(self, is_test, end="backend"):
        if is_test:
            return "LuoLin", "罗林"
        else:
            fixed_userid = hget("q7link_fixed_duty", end).split(",")
            body = get("http://10.0.144.51:5000/api/verify/duty/users")
            role_duty_info = body.get("data").get(end)
            duty_user_ids = []
            duty_user_names = []
            for duty in role_duty_info:
                duty_user_ids.append(duty.get("user_id"))
                duty_user_names.append(duty.get("user_name"))
            if len(fixed_userid) > 0:
                duty_user_ids.extend(fixed_userid)
            return "|".join(duty_user_ids), ",".join(duty_user_names)

    # 获取值班目标分支集合
    def get_duty_branches(self):
        branches = set()
        try:
            mapping = get_branch_mapping()
            for bs in mapping.values():
                branches.update(bs.split(","))
        except Exception as e:
            logger.error(e)
        return branches

    # 获取项目所属端
    def get_project_end(self, projects):
        front_projects = {"front-theory", "front-goserver"}
        intersection = set(projects).intersection(front_projects)
        if len(intersection) > 0:
            return "front"
        else:
            return "backend"

    # 触发ops编译
    def ops_build(self, branch, skip=False, project=None, call_name=None):
        try:
            build_url = "http://ops.q7link.com:8000/qqdeploy/projectbuild/"
            if skip:
                return
            caller = "值班助手"
            if call_name is not None:
                caller = "{}-值班助手".format(call_name)
            params = {"branch": branch, "byCaller": caller}
            if project is not None:
                params["projects"] = project
            res = post_form(build_url, params)
            return res.get("data").get("taskid")
        except Exception as e:
            logger.error(e)
            return "-1"



