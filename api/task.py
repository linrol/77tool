import random
import string
import time
import re
from datetime import datetime, date, timedelta
from log import logger
from shell import Shell
from wxmessage import build_create_branch__msg, build_merge_branch_msg, build_move_branch_msg, msg_content
from redisclient import save_user_task, get_branch_mapping, hmset, hget
from common import Common
branch_check_list = ["sprint", "stage-patch", "emergency1", "emergency"]


class Task(Common):
    def __init__(self, is_test=False):
        super().__init__()
        self.is_test = is_test

    def get_project(self, project_name):
        if project_name not in self.projects.keys():
            raise Exception("ERROR: 工程【{}】不存在".format(project_name))
        return self.projects.get(project_name)

    def get_project_branch(self, project_name, branch):
        project = self.get_project(project_name)
        return project.getBranch(branch)

    def get_feature_branch(self, source_branch, target_branch):
        s_not, t_not, _, _ = self.not_duty_branch(source_branch, target_branch)
        if (not s_not) and (not t_not):
            # 值班分支
            return None
        feature_info = hget("q7link-branch-feature", target_branch)
        if feature_info is None:
            sql = "select * from zt_project where code = '{}' and type='sprint'".format(target_branch)
            zt_project_info = self.zt_fetchone(sql)
            if zt_project_info is None:
                return None
            app = zt_project_info.get("app")
            pm = zt_project_info.get("PM")
            account = (pm if (app is None or app.isspace()) else app).replace(",", "")
            sql = "select * from zt_user where account = '{}'".format(account)
            zt_user_info = self.zt_fetchone(sql)
            if zt_user_info is None:
                return None
            leader_user = zt_user_info.get("realname", None)
            version = self.gen_feature_version(source_branch)
            self.save_branch_feature(target_branch, source_branch, version,
                                     leader_user)
            return version, self.name2userid(leader_user), leader_user
        source = feature_info.split("@")[0]
        if source != source_branch:
            raise Exception("ERROR: 特性分支初始化的来源分支必须为【{}】".format(source))
        version = feature_info.split("@")[1]
        approve = feature_info.split("@")[2]
        return version, self.name2userid(approve), approve

    def get_new_project(self, target, project_names):
        exclude_projects = ["build", "parent", "testapp"]
        projects = list(filter(
            lambda name:
            self.get_project_branch(name, target) is None
            and name not in exclude_projects, project_names.split(",")))
        if len(projects) < 1:
            raise Exception("ERROR: \n" + "工程【{}】目标分支【{}】已存在!!!".format(
                project_names, target))
        return projects

    def gen_feature_version(self, branch):
        prefix = self.get_branch_version(branch).get("framework")
        last_version = ''.join(random.sample(string.ascii_letters, 6))
        return "{}.{}-SNAPSHOT".format(prefix.replace("-SNAPSHOT", ""),
                                       last_version)

    # 判断非值班分支
    def not_duty_branch(self, source, target):
        mapping = get_branch_mapping()
        match_source = None
        match_target = []
        for k, v in mapping.items():
            match = re.match("^{}$".format(k), source)
            if not match:
                continue
            match_source = match.group()
            match_target = v.split(",")
        s_not_duty = match_source is None
        target_name, target_date = self.get_branch_date(target)
        t_not_duty = target_date is None or target_name not in match_target
        return s_not_duty, t_not_duty, mapping.keys(), match_target

    def check_new_branch(self, source, target, user_name):
        tips = "\n是否需要拉特性分支，如需请按以下格式初始化(可修改分支版本号，负责人等信息)：" + \
               "\n=============================================================" + \
               "\n操　　作：初始化特性分支" + \
               "\n来源分支：" + source + \
               "\n目标分支：" + target + \
               "\n分支版本号：{}" + \
               "\n分支负责人：" + user_name
        s_not, t_not, sources, targets = self.not_duty_branch(source, target)
        if s_not:
            error = "来源分支非值班系列【{}】{}"
            tips = tips.format(self.gen_feature_version(source))
            raise Exception(error.format(",".join(sources), tips))
        target_name, target_date = self.get_branch_date(target)
        if t_not:
            error = "目标分支非值班系列【{}】{}"
            tips = tips.format(self.gen_feature_version(source))
            raise Exception(error.format(",".join(targets), tips))
        week_later = (datetime.now() + timedelta(days=-7)).strftime("%Y%m%d")
        if int(week_later) > int(target_date):
            raise Exception("目标分支的上线日期过小，请检查分支名称日期")

    # 创建拉值班分支的任务
    def new_branch_task(self, crop, req_id, req_name, duty_id, duty_name,
        source, target, project_names):
        feature_info = self.get_feature_branch(source, target)
        if feature_info is not None:
            return self.new_feature_branch_task(crop, req_id, req_name, source,
                                                target, project_names,
                                                *feature_info)
        self.check_new_branch(source, target, req_name)
        need_projects = self.get_new_project(target, project_names)
        split = self.split_multi_source(source, target, need_projects)
        notify_req = None
        for priority, projects in split.items():
            if len(projects) < 1:
                continue
            task_id = "branch_new@{}".format(int(time.time()))
            logger.info("task_id" + task_id)
            project_str = ",".join(projects)
            notify_duty, notify_req = build_create_branch__msg(req_id, req_name,
                                                               duty_name,
                                                               task_id,
                                                               priority,
                                                               target,
                                                               project_str)
            # 发送值班人审核通知
            body = crop.send_template_card(duty_id, notify_duty)
            # 记录任务
            task_code = body.get("response_code")
            content = "{}#{}#{}#{}#None#{}#{}".format(req_id, priority, target,
                                                      project_str,
                                                      str(self.is_test),
                                                      task_code)
            save_user_task(task_id, content)
        crop.send_text_msg(req_id, notify_req)
        task_brief = "{}#{}#{}".format(source, target, project_names)
        return True, "new branch task[{}] success".format(task_brief)

    # 创建拉特性分支的任务
    def new_feature_branch_task(self, crop, req_user_id, req_user_name,
        source, target, project_names, version, approve_id, approve_name):
        project_str = ",".join(self.get_new_project(target, project_names))
        task_id = "branch_new@{}".format(int(time.time()))
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
        crop.send_text_msg(req_user_id, notify_req)
        return True, "new branch task[{}] success".format(task_id)

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

    # 检查版本号
    def check_version(self, branch, crop):
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
        user_ids, _ = self.get_duty_info(True)
        ret, msg = Shell(self.is_test, user_ids).check_version(branch_names)
        logger.info(branch + ":" + msg)
        if not ret:
            for user_id in user_ids.split("|"):
                user_msg = msg.replace("user_id=", "user_id={}".format(user_id))
                crop.send_text_msg(user_id, user_msg)
        return ret, msg

    def clear_dirty_branch(self, user_id, branch_name, crop):
        if self.is_trunk(branch_name):
            return
        ret, msg = Shell(self.is_test, user_id).clear_branch(branch_name)
        crop.send_text_msg(user_id, msg)

    # 发生清理脏分支通知
    def clear_dirty_branch_notice(self, crop):
        # self.save_branch_pushed()
        clear_branch_msg = "您创建的分支【{}】超过三个月不存在提交记录，可能为脏分支，请确认是否需要删除？\n<a href=\"https://branch.linrol.cn/branch/clear?user_id={}&branch={}\">点击删除</a>\n无需删除请忽略"
        dirty_branches = self.get_dirty_branches()
        for branch, author in dirty_branches.items():
            username = hget("q7link-git-user", author)
            if username is None:
                continue
            user_id = self.name2userid(username)
            if user_id == "LuoLin":
                crop.send_text_msg(user_id, clear_branch_msg.format(branch, user_id, branch))
            logger.info(clear_branch_msg.format(branch, user_id, branch))

    # 获取可能的脏分支（三个月以上不存在提交记录）
    def get_dirty_branches(self):
        git_branches = self.project_build.getProject().branches.list(all=True)
        dirty_branches = {}
        for branch in git_branches:
            # 过滤特定分支
            branch_name = branch.name
            if self.is_trunk(branch_name):
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
            author = hget("q7link-branch-pushed", branch_name)
            if author is None:
                continue
            dirty_branches[branch_name] = author
        return dirty_branches

    def save_branch_pushed(self):
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
            logger.info("保存分支创建信息第{}页面".format(i))
            if len(branch_created) < 1:
                continue
            hmset("q7link-branch-pushed", branch_created)

    # 校正分支版本号
    def branch_correct(self, user_id, branch, project, crop):
        shell = Shell(self.is_test, user_id, self.master, branch)
        params = "none other={}".format(project)
        _, msg = shell.build_package(params, "hotfix,all", True)
        logger.info("branch correct [{}] [{}] ret[{}]".format(branch, project, msg))
        crop.send_text_msg(user_id, msg)
        return msg

    # 拆分项目的来源分支
    def split_multi_source(self, source, target, projects):
        ret = {source: projects.copy()}
        over_source = self.stage_global
        if source != self.stage:
            return ret
        end = "backend"
        branch = self.get_branch_created_source(end, over_source)
        if branch is None:
            return ret
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
        before_min = (datetime.now() - timedelta(minutes=600)).isoformat()
        group = self.get_project('parent').getGroup('backend')
        # 发送待合并通知
        opened_mr_list = group.mergerequests.list(state='opened', all=True,
                                                  created_after=before_min)
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
            assignee_user_id = self.name2userid(assignee_name)
            logger.info("send mr to {} url {}".format(assignee_user_id,
                                                      mr_target_msg))
            crop.send_text_msg(assignee_user_id, mr_target_msg)
            hmset("q7link-branch-merge", {mr_key: assignee_name})

        # 发送已合并通知
        merged_mr_list = group.mergerequests.list(state='merged', all=True,
                                                  created_after=before_min)
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
            # if author_id == merged_userid and not is_data_pre:
            #     continue
            merged_username = hget("q7link-git-user", merged_userid)
            if merged_username is None:
                merged_username = merged_userid
            if is_data_pre:
                author_userid = mr.title.replace(data_pre_str, "")
                author_name = author_userid
            else:
                author_name = hget("q7link-git-user", author_id)
                if not author_name:
                    logger.error("author id [{}] not found".format(author_id))
                    continue
                author_userid = self.name2userid(author_name)
            project_full = mr.references.get("full").split("!")[0]
            _, project = project_full.rsplit("/", 1)
            build_id = "-1"
            if project in self.projects.keys():
                build_id = self.ops_build(mr.target_branch, False,
                                          project_full, author_name)
            mr_source_msg = msg_content["mr_source"].format(mr.web_url,
                                                            project,
                                                            merged_username,
                                                            build_id)
            logger.info("send mr to {} url {}".format(author_userid,
                                                      mr_source_msg))
            hmset("q7link-branch-merge", {mr_key: author_userid})
            crop.send_text_msg(author_userid, mr_source_msg)

    # 发送代码合并任务
    def build_branch_task(self, branches, modules, clusters, crop):
        ret = []
        backend_modules = modules.intersection({"apps", "global"})
        if len(backend_modules) > 0:
            task_id = self.build_backend_merge(backend_modules, branches,
                                               clusters, crop)
            ret.append(task_id)
        if len(modules.intersection({"web", "h5", "front-theory"})) > 0:
            front_modules = ["front-theory"]
            task_id = self.build_front_merge(front_modules, branches,
                                             clusters, crop)
            ret.append(task_id)
        if len(modules.intersection({"trek", "front-goserver"})) > 0:
            front_modules = ["front-goserver"]
            task_id = self.build_front_merge(front_modules, branches,
                                             clusters, crop)
            ret.append(task_id)
        return ",".join(ret)

    # 发送后端代码合并任务
    def build_backend_merge(self, modules, branches, clusters, crop):
        try:
            user_ids, _ = self.get_duty_info(self.is_test)
            source, target = self.get_merge_branch(branches, clusters, "build")
            is_global = "global" in modules
            params = [user_ids, source, target, modules, clusters, crop]
            if is_global and "sprint" in source:
                if self.has_release(source):
                    raise Exception("sprint deploy global,all release not move")
                # sprint发布到global & 分支未封板，将global模块迁移至stage-global
                target = self.stage_global
                params[2] = target
                return self.send_branch_action("move", *params)
            task_id = self.send_branch_action("merge", *params)
            return task_id
        except Exception as err:
            logger.exception(err)
            return str(err)

    # 发送前端代码合并任务
    def build_front_merge(self, modules, branches, clusters, crop):
        try:
            user_ids, _ = self.get_duty_info(self.is_test, "front")
            module = modules[0]
            source, target = self.get_merge_branch(branches, clusters, module)
            return self.send_branch_action("merge", user_ids, source, target,
                                           modules, clusters, crop)
        except Exception as err:
            logger.exception(err)
            return str(err)

    # 检测分支版本号是否都为发布包（所有模块）
    def has_release(self, branch):
        try:
            versions = self.get_branch_version(branch).values()
            for version in versions:
                if "SNAPSHOT" in version:
                    return False
            return True
        except Exception as err:
            logger.exception(err)
            return True

    # 发送分支操作（迁移/合并）任务
    def send_branch_action(self, action, user_ids, source, target, modules, clusters, crop):
        # 发送合并代码通知
        task_id = "branch_{}@{}".format(action, int(time.time()))
        if action == "move":
            task_params = build_move_branch_msg(source, target,
                                                ",".join(modules),
                                                ",".join(clusters),
                                                task_id)
        elif action == "merge":
            task_params = build_merge_branch_msg(source, target,
                                                 ",".join(modules),
                                                 ",".join(clusters),
                                                 task_id)
        else:
            raise Exception("action error")
        body = crop.send_template_card(user_ids, task_params)
        # 记录任务
        task_code = body.get("response_code")
        content = "{}#{}#{}#{}#None#{}#{}".format(user_ids,
                                                  source,
                                                  target,
                                                  ",".join(modules),
                                                  str(self.is_test),
                                                  task_code)
        logger.info("task[{}] content[{}]".format(task_id, content))
        save_user_task(task_id, content)
        return task_id

    def branch_seal(self, body):
        logger.info("branch_seal:" + str(body))
        response = {}
        user_id, branch, projects, is_seal = body.get("user_id"), body.get("branch"), body.get("projects"), body.get("is_seal") == "true"
        modules = []
        shell = Shell(user_id, self.is_test, self.master, branch)
        access = "none" if is_seal else "hotfix"
        for project in projects:
            is_backend = project in ["apps", "global"]
            if is_backend:
                modules = [project] if len(modules) == 0 else ["all"]
            if project not in self.projects.keys() and not is_backend:
                ret, msg = self.protect_git_branch(branch, project, access)
            else:
                ret, msg = self.protect_branch(branch, access, [project])
            response[project] = {"ret": ret, "msg": msg}
        front_version = body.get("front_version", "").strip()
        if len(front_version) > 0:
            modules.append("front-apps=reimburse:{}".format(front_version))
        if is_seal and len(modules) > 0:
            # 后端封版，模块包含apps，global则构建发布包
            protect = access + "," + modules[0]
            is_build = body.get("is_build", "") == 'true'
            shell.build_package(" ".join(modules), protect, is_build)
        return response

    # 检查是否为发布包
    def release_check(self, body):
        logger.info("release_check:" + str(body))
        branch = body.get("branch")
        projects = body.get("projects")
        for project in projects:
            if project not in ["apps", "global"]:
                continue
            check_categories = self.category_mapping.get(project)
            branch_versions = self.get_branch_version(branch)
            for p, v in branch_versions.items():
                category = self.project_category.get(p)
                if category not in check_categories:
                    continue
                if "SNAPSHOT" not in v:
                    continue
                raise Exception("工程【{}】还未构建发布包，当前版本号【{}】".format(p, v))
        return "发布包版本号检查通过"

    # 对比两个分支的版本号
    def compare_branch_version(self, left, right):
        left_versions = self.get_branch_version(left)
        right_versions = self.get_branch_version(right)
        return left_versions == right_versions