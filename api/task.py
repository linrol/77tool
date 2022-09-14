import os
import sys
import time
import yaml
from datetime import datetime, date
from log import logger
from shell import Shell
from wxmessage import build_create_branch__msg
from redisclient import save_create_branch_task, get_branch_mapping, hmset, hget

sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
from branch import utils

branch_check_list = ["sprint", "stage-patch", "emergency1", "emergency"]


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
        mapping = get_branch_mapping()
        if source_branch not in mapping.values():
            raise Exception("来源分支非值班系列【{}】，暂不支持".format(",".join(mapping.values())))
        target_name = None
        target_date = None
        for k, v in mapping.items():
            if k in target_branch:
                target_name = k
                target_date = target_branch.replace(k, "")
        if target_name is None or target_date is None:
            raise Exception("目标分支非值班系列【{}】".format(",".join(mapping.keys())))
        if len(target_date) != 8:
            raise Exception("目标分支上线日期解析错误，请检查分支名称")
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

    # 检查版本号
    def check_version(self, user_id, branch, send_text_msg):
        branch_name = None
        branch_date = None
        for name in branch_check_list:
            if name not in branch:
                continue
            if len(branch.replace(name, "")) != 8:
                continue
            branch_name = name
            branch_date = branch.replace(name, "")
            break
        if branch_name is None:
            return True, "not check branch"
        if not branch_date.isdigit():
            return True, "branch data invalid"
        index = branch_check_list.index(branch_name)
        branch_list = []
        for check_branch in branch_check_list[index:]:
            branch_list.append(check_branch + branch_date)
        branch_names = ",".join(branch_list)
        if len(branch_list) < 2:
            return True, "branch({}) length less than one".format(branch_names)
        ret, msg = Shell(self.is_test, user_id).check_version(branch_names)
        logger.info(branch + ":" + msg)
        if not ret:
            send_text_msg(user_id, msg + "\n请注意可能需要手动调整!!!")
        return ret, msg

    def clear_dirty_branch(self, user_id, branch_name, send_text_msg):
        if branch_name in ('stage', 'master', 'master1'):
            return
        ret, msg = Shell(self.is_test, user_id).clear_branch(branch_name)
        send_text_msg(user_id, msg)

    # 发生清理脏分支通知
    def clear_dirty_branch_notice(self, crop):
        # self.save_branch_created()
        clear_branch_msg = "您创建的分支【{}】超过三个月不存在提交记录，可能为脏分支，请确认是否需要删除？\n<a href=\"https://branch.linrol.cn/branch/clear?user_id={}&branch={}\">点击删除</a>\n无需删除请忽略"
        dirty_branches = self.get_dirty_branches()
        for branch, author in dirty_branches.items():
            username = hget("q7link-git-user", author)
            if username is None:
                continue
            user_id = crop.get_user_id(username)
            if user_id == "LuoLin":
                crop.send_text_msg(user_id, clear_branch_msg.format(branch, user_id, branch))
            print(clear_branch_msg.format(branch, user_id, branch))

    # 获取可能的脏分支（三个月以上不存在提交记录）
    def get_dirty_branches(self):
        git_branches = self.project_build.getProject().branches.list(all=True)
        dirty_branches = {}
        for branch in git_branches:
            # 过滤特定分支
            branch_name = branch.name
            if branch_name in ['stage', 'master', 'master1']:
                continue
            # 过滤三个月以上未提交的分支
            today = date.today()
            date1 = datetime.strptime(today.strftime("%Y-%m-%d"),
                                      "%Y-%m-%d")
            date2 = datetime.strptime(branch.commit.get("created_at")[0:10],
                                      "%Y-%m-%d")
            dirty_branch = (date1 - date2).days < 90
            if dirty_branch:
                continue
            author = hget("q7link-branch-created", branch_name)
            if author is None:
                continue
            dirty_branches[branch_name] = author
        return dirty_branches

    def save_branch_created(self):
        for i in range(1, 150):
            branch_created = {}
            events = self.project_build.getProject().events.list(
                action='pushed', page=i, per_page=100, sort='asc')
            for e in events:
                if e.action_name != 'pushed new':
                    continue
                branch = e.push_data.get('ref')
                if branch is None:
                    continue
                username = e.author_username
                if username is None:
                    continue
                branch_created[branch] = username
            print("保存分支创建信息第{}页面".format(i))
            if len(branch_created) < 1:
                continue
            hmset("q7link-branch-created", branch_created)


