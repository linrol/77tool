import os
import sys
import re
import time
from datetime import datetime
import yaml

from wxmessage import build_create_branch__msg
from redisclient import save_create_branch_task

sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
from branch import utils


class Task:
    def __init__(self, is_test=False):
        os.chdir("../branch/")
        self.is_test = is_test
        self.projects = utils.project_path()
        self.project_build = self.get_project('build')

    def get_project(self, project_name):
        if project_name not in self.projects.keys():
            raise Exception("ERROR: 工程【{}】不存在".format(project_name))
        return self.projects.get(project_name)

    def check_create_branch(self, source_branch, target_branch, project_names):
        if source_branch not in ['stage', 'master', 'master1']:
            raise Exception("来源分支非值班系列【stage或master】，暂不支持")
        pattern = r"([a-zA-Z-]+|[20]\d{7})"
        target_branch_info = re.findall(pattern, target_branch)
        if len(target_branch_info) != 2:
            raise Exception("目标分支格式错误，请检查分支名称!")
        target_name = target_branch_info[0]
        target_date = target_branch_info[1]
        if target_name + target_date != target_branch:
            raise Exception("目标分支上线日期解析错误，请检查分支名称")
        if target_name not in ['emergency', 'sprint', 'stage-patch']:
            raise Exception("目标分支非值班系列【emergency、stage-patch、sprint】")
        now = datetime.now().strftime("%Y%m%d")
        if int(now) > int(target_date):
            raise Exception("目标分支的上线日期须大于等于当天，请检查分支名称日期")
        need_project_list = list(filter(
            lambda name: self.get_project(name).getBranch(
                target_branch) is None, project_names.split(",")))
        if len(need_project_list) < 1:
            raise Exception("ERROR: \n" + "工程【{}】目标分支【{}】已存在!!!".format(
                project_names, target_branch))
        return target_name, target_date, ",".join(need_project_list)

    # 创建拉分支的任务
    def build_create_branch_task(self, send_template_card, req_user_id,
        req_user_name, duty_user_id, duty_user_name, source, target,
        project_names):
        try:
            _, _, need_projects = self.check_create_branch(source, target,
                                                           project_names)
            task_id = "{}@{}@{}@{}".format(req_user_id, source, target,
                                           int(time.time()))
            notify_duty, notify_req = build_create_branch__msg(req_user_id,
                                                               req_user_name,
                                                               duty_user_name,
                                                               task_id, source,
                                                               target,
                                                               need_projects)
            # 发送值班人审核通知
            body = send_template_card(duty_user_id, notify_duty)
            # 记录任务
            task_code = body.get("response_code")
            task_content = "{}@{}@{}".format(task_code, need_projects, str(self.is_test))
            save_create_branch_task(task_id, task_content)
            return notify_req
        except Exception as err:
            return str(err)

    def compare_version(self, left_branch, right_branch):
        ret = {}
        if self.project_build.getBranch(right_branch) is None:
            return ret
        left_version = self.get_branch_version(left_branch)
        right_version = self.get_branch_version(right_branch)
        for k, v in right_version.items():
            if "SNAPSHOT" not in v:
                continue
            if k == "reimburse":
                continue
            left = left_version.get(k)
            if left is None:
                continue
            if "SNAPSHOT" in left:
                continue
            left_base = left.rsplit(".", 1)[0]
            left_min = left.rsplit(".", 1)[1]
            right = v.replace("-SNAPSHOT", "")
            right_base = right.rsplit(".", 1)[0]
            right_min = right.rsplit(".", 1)[1]
            if left_base != right_base:
                continue
            if int(right_min) - int(left_min) < 3:
                ret[k] = "({},{})".format(left, v)
        return ret


    # 获取指定分支的版本号
    def get_branch_version(self, branch):
        config_yaml = self.get_project_build_config(branch)
        version = {}
        for group, item in config_yaml.items():
            if type(item) is not dict:
                continue
            for k, v in item.items():
                version[k] = v
        if len(version) < 1:
            raise Exception("根据分支【{}】获取工程版本号失败".format(branch))
        return version

    # 根据工程名称获取指定分支的远程文件
    def get_project_build_config(self, branch_name):
        file = self.project_build.getProject().files.get(file_path='config.yaml', ref=branch_name)
        if file is None:
            raise Exception("工程【build】分支【{}】不存在文件【config.yaml】".format(branch_name))
        config_yaml = yaml.load(file.decode(), Loader=yaml.FullLoader)
        return config_yaml
