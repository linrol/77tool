import os
import sys
import time
import yaml
import re
from datetime import datetime, date, timedelta
from log import logger
from shell import Shell
from wxmessage import build_create_branch__msg, build_merge_branch_msg, build_move_branch_msg, msg_content, is_chinese
from redisclient import save_user_task, get_branch_mapping, hmset, hget

sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/data/backend/branch-manage")
from branch import utils

branch_check_list = ["sprint", "stage-patch", "emergency1", "emergency"]
target_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'


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

    def get_feature_branch(self, source_branch, target_branch, crop):
        feature_info = hget("q7link-branch-feature", target_branch)
        if feature_info is None:
            return None
        source = feature_info.split("@")[0]
        if source != source_branch:
            raise Exception("ERROR: 特性分支初始化的来源分支必须为【{}】".format(source))
        version = feature_info.split("@")[1]
        approve = feature_info.split("@")[2]
        return version, crop.user_name2id(approve), approve

    def get_new_project(self, target, project_names):
        need_project_list = list(filter(
            lambda name: self.get_project(name).getBranch(target) is None,
            project_names.split(",")))
        if len(need_project_list) < 1:
            raise Exception("ERROR: \n" + "工程【{}】目标分支【{}】已存在!!!".format(
                project_names, target))
        return need_project_list

    def check_new_branch(self, source_branch, target_branch, user_name):
        tips = "\n是否需要拉特性分支，如需请按以下格式初始化：" + \
               "\n===================================" + \
               "\n操　　作：初始化特性分支" + \
               "\n来源分支：" + source_branch + \
               "\n目标分支：" + target_branch + \
               "\n分支负责人：" + user_name
        mapping = get_branch_mapping()
        match_source = None
        match_target = []
        for k, v in mapping.items():
            match = re.match("^{}$".format(k), source_branch)
            if not match:
                continue
            match_source = match.group()
            match_target = v.split(",")
        if match_source is None:
            raise Exception("来源分支非值班系列【{}】{}".format(",".join(mapping.keys()), tips))
        target_name = None
        target_date = None
        if re.search(target_regex, target_branch):
            target_date = re.search(target_regex, target_branch).group()
            target_name = target_branch.replace(target_date, "")
        if target_date is None or target_name not in match_target:
            raise Exception("目标分支非值班系列【{}】{}".format(",".join(match_target), tips))
        now = datetime.now().strftime("%Y%m%d")
        if int(now) > int(target_date):
            raise Exception("目标分支的上线日期须大于等于当天，请检查分支名称日期")

    # 创建拉值班分支的任务
    def new_branch_task(self, crop, req_id, req_name, duty_id, duty_name,
        source, target, project_names):
        try:
            feature_info = self.get_feature_branch(source, target, crop)
            if feature_info is not None:
                return self.new_feature_branch_task(crop, req_id, req_name,
                                                    source, target,
                                                    project_names,
                                                    *feature_info)
            self.check_new_branch(source, target, req_name)
            need_projects = self.get_new_project(target, project_names)
            split = self.split_multi_source(source, target, need_projects)
            notify_req = None
            for priority, projects in split.items():
                if len(projects) < 1:
                    continue
                task_id = "branch_new@{}@{}".format(req_id.replace("@", "").replace(".", ""),
                                                    int(time.time()))
                logger.info("task_id" + task_id)
                project_str = ",".join(projects)
                notify_duty, notify_req = build_create_branch__msg(req_id,
                                                                   req_name,
                                                                   duty_name,
                                                                   task_id,
                                                                   priority,
                                                                   target,
                                                                   project_str)
                # 发送值班人审核通知
                body = crop.send_template_card(duty_id, notify_duty)
                # 记录任务
                task_code = body.get("response_code")
                content = "{}#{}#{}#{}#None#{}#{}".format(req_id,
                                                          priority,
                                                          target,
                                                          project_str,
                                                          str(self.is_test),
                                                          task_code)
                save_user_task(task_id, content)
            return notify_req
        except Exception as err:
            return str(err)

    # 创建拉特性分支的任务
    def new_feature_branch_task(self, crop, req_user_id, req_user_name,
        source, target, project_names, version, approve_id, approve_name):
        project_str = ",".join(self.get_new_project(target, project_names))
        task_id = "branch_new@{}@{}".format(req_user_id, int(time.time()))
        notify_approve, notify_req = build_create_branch__msg(req_user_id,
                                                              req_user_name,
                                                              approve_name,
                                                              task_id,
                                                              source,
                                                              target,
                                                              project_str)
        # 发送分支负责人审核通知
        body = crop.send_template_card(approve_id, notify_approve)
        # 记录任务
        task_code = body.get("response_code")
        task_content = "{}#{}#{}#{}#{}#{}#{}".format(req_user_id, source,
                                                     target,
                                                     project_str, version,
                                                     str(self.is_test),
                                                     task_code)
        save_user_task(task_id, task_content)
        return notify_req

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
    def check_version(self, user_ids, branch, crop):
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
        ret, msg = Shell(self.is_test, user_ids).check_version(branch_names)
        logger.info(branch + ":" + msg)
        if not ret:
            for user_id in user_ids.split("|"):
                user_msg = msg.replace("user_id=", "user_id={}".format(user_id))
                crop.send_text_msg(user_id, user_msg)
        return ret, msg

    def clear_dirty_branch(self, user_id, branch_name, crop):
        if branch_name in ('stage', 'master', 'master1'):
            return
        ret, msg = Shell(self.is_test, user_id).clear_branch(branch_name)
        crop.send_text_msg(user_id, msg)

    # 发生清理脏分支通知
    def clear_dirty_branch_notice(self, crop):
        # self.save_branch_created()
        clear_branch_msg = "您创建的分支【{}】超过三个月不存在提交记录，可能为脏分支，请确认是否需要删除？\n<a href=\"https://branch.linrol.cn/branch/clear?user_id={}&branch={}\">点击删除</a>\n无需删除请忽略"
        dirty_branches = self.get_dirty_branches()
        for branch, author in dirty_branches.items():
            username = hget("q7link-git-user", author)
            if username is None:
                continue
            user_id = crop.user_name2id(username)
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

    # 校正分支版本号
    def branch_correct(self, user_id, branch, project, crop):
        shell = Shell(self.is_test, user_id, "master", branch)
        _, msg = shell.build_package("correct={}".format(project), "hotfix",
                                     True)
        logger.info("branch correct [{}] [{}] ret[{}]".format(branch, project,
                                                              msg))
        crop.send_text_msg(user_id, msg)
        return msg

    # 拆分项目的来源分支
    def split_multi_source(self, source, target, projects):
        ret = {source: projects.copy()}
        over_source = "stage-global"
        if source != 'stage':
            return ret
        info = hget("q7link-branch-created", over_source)
        if info is None:
            return ret
        branch = info.split("#")[0]
        if target != branch:
            return ret
        for p in projects:
            if self.projects.get(p).getBranch(over_source) is None:
                continue
            ret.setdefault(over_source, []).append(p)
            ret.get(source).remove(p)
        return ret

    # 发送mr提醒通知
    def send_mr_notify(self, crop):
        before_five_min = (datetime.now() - timedelta(minutes=600)).isoformat()
        group = self.get_project('parent').getGroup('backend')
        # 发送待合并通知
        opened_mr_list = group.mergerequests.list(state='opened',
                                                  created_after=before_five_min)
        for mr in opened_mr_list:
            if mr.assignee is None:
                continue
            mr_key = "opened_" + mr.web_url
            if hget("q7link-branch-merge", mr_key) is not None:
                continue
            author_id = mr.author.get("username")
            git_assignee_id = mr.assignee.get("username")
            if author_id == git_assignee_id:
                continue
            author_name = hget("q7link-git-user", author_id)
            if author_name is None:
                author_name = author_id
            assignee_name = hget("q7link-git-user", git_assignee_id)
            if assignee_name is None:
                logger.error("git assignee id [{}] not found".format(git_assignee_id))
                continue
            _, project = mr.references.get("full").split("!")[0].rsplit("/", 1)
            mr_target_msg = msg_content["mr_target"].format(author_name,
                                                            mr.title,
                                                            project,
                                                            mr.source_branch,
                                                            mr.target_branch,
                                                            mr.web_url)
            assignee_user_id = crop.user_name2id(assignee_name)
            logger.info("send mr to {} url {}".format(assignee_user_id,
                                                      mr_target_msg))
            crop.send_text_msg(assignee_user_id, mr_target_msg)
            hmset("q7link-branch-merge", {mr_key: assignee_name})

        # 发送已合并通知
        merged_mr_list = group.mergerequests.list(state='merged',
                                                  created_after=before_five_min)
        for mr in merged_mr_list:
            if mr.merged_by is None:
                continue
            mr_key = "merged_" + mr.web_url
            if hget("q7link-branch-merge", mr_key) is not None:
                continue
            data_pre_str = "<数据预置>前端多列表方案预置-"
            is_data_pre = data_pre_str in mr.title
            author_id = mr.author.get("username")
            merged_userid = mr.merged_by.get("username")
            if author_id == merged_userid and not is_data_pre:
                continue
            merged_username = hget("q7link-git-user", merged_userid)
            if merged_username is None:
                merged_username = merged_userid
            if is_data_pre:
                author_userid = mr.title.replace(data_pre_str, "")
            else:
                author_name = hget("q7link-git-user", author_id)
                if not author_name:
                    logger.error("author id [{}] not found".format(author_id))
                    continue
                author_userid = crop.user_name2id(author_name)
            _, project = mr.references.get("full").split("!")[0].rsplit("/", 1)
            mr_source_msg = msg_content["mr_source"].format(project,
                                                            merged_username,
                                                            mr.web_url)
            logger.info("send mr to {} url {}".format(author_userid,
                                                      mr_source_msg))
            crop.send_text_msg(author_userid, mr_source_msg)
            hmset("q7link-branch-merge", {mr_key: author_userid})

    # 发送代码合并任务
    def send_branch_merge(self, branches, groups, clusters, crop):
        user_ids, _ = crop.get_duty_info(self.is_test, ["LuoLin"])
        ret = []
        for source in branches:
            if is_chinese(source):
                continue
            sprint_deploy_global = "sprint" in source and "global" in clusters
            if sprint_deploy_global:
                # 班车分支发布至集群0，需sprint分支迁移至stage-global
                target = "stage-global"
                task_id = self.send_branch_move(user_ids, source, target,
                                                groups, clusters, crop)
                ret.append(task_id)
                continue
            sprint_deploy_cluster0 = "sprint" in source and "集群0" in clusters
            if sprint_deploy_cluster0 and len(clusters) > 1:
                logger.error("sprint deploy unknown scene")
                continue
            if sprint_deploy_cluster0:
                # 班车分支发布至集群0，需把stage-global合并至sprint
                source = "stage-global"
            created_info = hget("q7link-branch-created", source)
            if created_info is None:
                continue
            if self.project_build.getBranch(source) is None:
                continue
            target = created_info.split("#")[0]
            if self.project_build.getBranch(target) is None:
                continue
            # 发送合并代码通知
            task_id = "branch_merge@{}@{}".format(user_ids, int(time.time()))
            _merge = build_merge_branch_msg(source, target, ",".join(clusters),
                                            task_id)
            body = crop.send_template_card(user_ids, _merge)
            # 记录任务
            task_code = body.get("response_code")
            content = "{}#{}#{}#{}#None#{}#{}".format(user_ids,
                                                      source,
                                                      target,
                                                      ",".join(groups),
                                                      str(self.is_test),
                                                      task_code)
            logger.info("task[{}] content[{}]".format(task_id, content))
            save_user_task(task_id, content)
            ret.append(task_id)
        return ",".join(ret)

    # 发送分支迁移任务
    def send_branch_move(self, user_ids, source, target, group, clusters, crop):
        # 发送合并代码通知
        task_id = "branch_move@{}@{}".format(user_ids, int(time.time()))
        _merge = build_move_branch_msg(source, target, ",".join(clusters),
                                        task_id)
        body = crop.send_template_card(user_ids, _merge)
        # 记录任务
        task_code = body.get("response_code")
        content = "{}#{}#{}#{}#None#{}#{}".format(user_ids,
                                                  source,
                                                  target,
                                                  group,
                                                  str(self.is_test),
                                                  task_code)
        logger.info("task[{}] content[{}]".format(task_id, content))
        save_user_task(task_id, content)
        return task_id


if __name__ == '__main__':
    Task().send_mr_notify(None)