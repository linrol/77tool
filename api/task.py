import random
import string
import time
import re
from datetime import datetime, date, timedelta
from log import logger
from shell import Shell
from wxmessage import send_create_branch_msg, build_merge_branch_msg, build_move_branch_msg, msg_content
from redisclient import save_user_task, save_task_depend, get_branch_mapping, hmset, hget, hdel
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

    def get_feature_branch(self, source_branch, target_branch, end, **user):
        s_duty, t_duty, _, _ = self.is_duty_branch(source_branch, target_branch)
        if s_duty and t_duty:
            # 值班分支
            return None
        if end == "front":
            applicant_id = user["applicant"][0]
            applicant_name = user["applicant"][1]
            return self.gen_feature_version(source_branch), applicant_id, applicant_name
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
            self.save_branch_feature(target_branch, source_branch, version, leader_user)
            return version, self.name2userid(leader_user), leader_user
        source = feature_info.split("@")[0]
        if source != source_branch:
            logger.info("Waring: 特性分支创建时来源分支为【{}】".format(source))
            # raise Exception("Waring: 特性分支创建时来源分支为【{}】".format(source))
        version = feature_info.split("@")[1]
        approve = feature_info.split("@")[2]
        return version, self.name2userid(approve), approve

    def filter_project(self, target, projects):
        project_str = ",".join(projects)
        projects = list(filter(lambda name: self.get_project_branch(name, target) is None, projects))
        if len(projects) < 1:
            raise Exception("ERROR: \n" + "工程【{}】目标分支【{}】已存在!!!".format(project_str, target))
        return projects

    def gen_feature_version(self, branch):
        prefix = self.get_branch_version(branch).get("framework")
        last_version = ''.join(random.sample(string.ascii_letters, 6))
        prefix = re.match("[0-9][0-9.]*", prefix).group()
        return "{}.{}-SNAPSHOT".format(prefix, last_version).replace("..", ".")

    # 判断值班分支
    def is_duty_branch(self, source, target):
        mapping = get_branch_mapping()
        match_source = None
        match_target = []
        for k, v in mapping.items():
            match = re.match("^{}$".format(k), source)
            if not match:
                continue
            match_source = match.group()
            match_target = v.split(",")
        s_duty = match_source is not None
        target_name, target_date = self.get_branch_date(target)
        t_duty = target_date is not None and target_name in match_target
        return s_duty, t_duty, mapping.keys(), match_target

    def check_new_branch(self, source, target, user_name):
        tips = "\n是否需要拉特性分支，如需请按以下格式初始化(可修改分支版本号，负责人等信息)：" + \
               "\n=============================================================" + \
               "\n操　　作：初始化特性分支" + \
               "\n来源分支：" + source + \
               "\n目标分支：" + target + \
               "\n分支版本号：{}" + \
               "\n分支负责人：" + user_name
        s_duty, t_duty, sources, targets = self.is_duty_branch(source, target)
        if not s_duty:
            error = "来源分支非值班系列【{}】{}"
            tips = tips.format(self.gen_feature_version(source))
            raise Exception(error.format(",".join(sources), tips))
        target_name, target_date = self.get_branch_date(target)
        if not t_duty:
            error = "目标分支非值班系列【{}】{}"
            tips = tips.format(self.gen_feature_version(source))
            raise Exception(error.format(",".join(targets), tips))
        week_later = (datetime.now() + timedelta(days=-7)).strftime("%Y%m%d")
        if int(week_later) > int(target_date):
            raise Exception("目标分支的上线日期过小，请检查分支名称日期")

    # 创建拉值班分支的任务
    def new_branch_task(self, crop, end, source, target, projects, **user):
        projects = self.filter_project(target, projects)
        feature_info = self.get_feature_branch(source, target, end, **user)
        if feature_info is None:
            # 值班分支
            version = None
            self.check_new_branch(source, target, user["applicant"][1])
        else:
            # 特性分支
            version = feature_info[0]
            user["watchman"] = feature_info[1:]
        multi_source = self.split_multi_source(source, target, projects)
        for source, projects in multi_source.items():
            if len(projects) < 1:
                continue
            task_id = "branch_new@{}".format(int(time.time()))
            content = send_create_branch_msg(crop, source, target, projects,
                                             task_id, str(version), **user)
            # 记录任务
            logger.info("add task[{}->{}]".format(task_id, content))
            save_user_task(task_id, str(self.is_test) + "#" + content)
        ret = "{}->{}->{}".format(source, target, ",".join(projects))
        return True, "new branch task[{}] success".format(ret)

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
    def branch_correct(self, correct_user, branch, project, crop):
        shell = Shell(self.is_test, correct_user, self.master, branch)
        params = "none other={}".format(project)
        _, msg = shell.build_package(params, "hotfix,all", True)
        logger.info("branch correct [{}] [{}] ret[{}]".format(branch, project, msg))
        duty_users, _ = self.get_duty_info(True)
        crop.send_text_msg(duty_users, msg)
        return msg

    # 拆分项目的来源分支
    def split_multi_source(self, source, target, projects):
        ret = {source: projects.copy()}
        over_source = self.stage_global
        if source != self.stage:
            return ret
        branch = self.get_branch_created_source(self.backend, over_source)
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
        before_hours = (datetime.utcnow() - timedelta(minutes=180)).isoformat()
        group = self.get_project('parent').getGroup(self.backend)
        # 发送待合并通知
        opened_mr_list = group.mergerequests.list(state='opened', all=True,
                                                  created_after=before_hours)
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
                                                  updated_after=before_hours)
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
                if project not in ["build"]:
                    build_id = self.ops_build(mr.target_branch, False,
                                              project_full, author_name)
            mr_source_msg = msg_content["mr_source"].format(mr.web_url,
                                                            project,
                                                            merged_username,
                                                            build_id)
            logger.info("send mr to {} url {}".format(author_userid,
                                                      mr_source_msg))
            hmset("q7link-branch-merge", {mr_key: author_userid})
            hmset("q7link-branch-build", {build_id: author_userid})
            crop.send_text_msg(author_userid, mr_source_msg)

    # 发送编译结果通知
    def send_build_notify(self, crop, build_id, ret):
        user_id = hget("q7link-branch-build", build_id)
        if user_id is None:
            return
        ret_msg = "成功" if ret == "true" else "失败"
        build_msg = msg_content["build_ret"].format(build_id, ret_msg)
        crop.send_text_msg(user_id, build_msg)
        hdel("q7link-branch-build", build_id)

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
            push_global = "global" in modules
            is_sprint = "sprint" in source or "release" in source
            params = [user_ids, source, target, modules, clusters, crop]
            if is_sprint and push_global:
                if self.has_release(source):
                    raise Exception("sprint deploy global,all release not move")
                # sprint/release发布到global & 分支未封板，将global模块迁移至stage-global
                target = self.stage_global
                params[2] = target
                return self.send_branch_action("move", *params)
            task_id = self.send_branch_action("merge", *params)
            if not self.is_trunk(target):
                return task_id
            if not self.equals_version(self.stage, self.master):
                return task_id
            all_clusters = {"宁夏灰度集群0", "宁夏灰度集群1", "宁夏生产集群2", "宁夏生产集群3",
                            "宁夏生产集群4", "宁夏生产集群5", "宁夏生产集群6", "宁夏生产集群7"}
            push_all = len(set(clusters).intersection(all_clusters)) > 6
            if not push_all:
                return task_id
            # 当主干分支(stage,master)一致时且推送至所有集群时，合并到多个分支
            params[2] = self.stage if target == self.master else self.master
            task_id_2 = self.send_branch_action("merge", *params)
            save_task_depend(task_id, task_id_2)
            return task_id + "," + task_id_2
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
        time.sleep(2)
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
        content = "{}#{}#{}#{}#{}".format(str(self.is_test), task_code, source,
                                          target, ",".join(modules))
        logger.info("add task[{}->{}]".format(task_id, content))
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