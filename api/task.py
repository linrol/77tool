import os
import sys
import re
import time
from datetime import datetime
from wxmessage import build_create_branch__msg
from redisclient import save_create_branch_task, get_create_branch_task

sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
from branch import utils

class Task:
    def __init__(self, crop):
        os.chdir("../branch/")
        self.projects = utils.project_path()
        self.crop = crop

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
            raise Exception("目标分支的上线日期须大于等于当天，请检查分支名称")
        error = ''
        for name in project_names:
            project_branch = self.get_project(name).getBranch(target_branch)
            if project_branch is not None:
                error += "工程【{}】目标分支【{}】已存在\n".format(name, target_branch)
        if error != '':
            raise Exception("ERROR: \n" + error)
        return target_name, target_date

    # 创建拉分支的任务
    def build_create_branch_task(self, source, target, project_names, *user):
        req_user_id, req_user_name = user[0][0], user[0][1]
        duty_user_id, duty_user_name = user[1][0], user[1][1]
        try:
            self.check_create_branch(source, target, project_names)
            task_id = "{}@{}@{}@{}@{}".format(req_user_id, duty_user_id, source,
                                              target, int(time.time()))
            notify_duty_content, notify_req_content = build_create_branch__msg(
                req_user_id, req_user_name, duty_user_name, task_id, source,
                target, project_names)
            # 发送申请人的回执通知
            body = self.crop.send_text_msg(req_user_id, str(notify_req_content))
            # 发送值班人审核通知
            body = self.crop.send_template_card(duty_user_id,
                                                notify_duty_content)
            # 记录任务
            task_code = body.get("response_code")
            task_content = "{}@{}".format(task_code, ",".join(project_names))
            save_create_branch_task(task_id, task_content)
            return "build create branch task success"
        except Exception as err:
            # 发送申请人的回执通知
            self.crop.send_text_msg(req_user_id, str(err))
            return str(err)
