import os
import sys
import re
import time
from datetime import datetime
from wxmessage import build_create_branch__msg
from redisclient import save_create_branch_task

sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
from branch import utils


class Task:
    def __init__(self):
        os.chdir("../branch/")
        self.projects = utils.project_path()

    def get_project(self, project_name):
        if project_name not in self.projects.keys():
            raise Exception("ERROR: 工程【{}】不存在".format(project_name))
        return self.projects.get(project_name)

    def check_create_branch(self, source_branch, target_branch, project_names):
        if source_branch not in ['stage', 'master']:
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
            task_id = "{}@{}@{}@{}@{}".format(req_user_id, duty_user_id, source,
                                              target, int(time.time()))
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
            task_content = "{}@{}".format(task_code, need_projects)
            save_create_branch_task(task_id, task_content)
            return notify_req
        except Exception as err:
            return str(err)
