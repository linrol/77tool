import random
import string
import time
import re
from datetime import datetime, date, timedelta
from log import logger
from shell import Shell
from wxmessage import send_create_branch_msg, build_merge_branch_msg, build_move_branch_msg, msg_content
from redisclient import save_user_task, get_branch_mapping, hmset, hget, hdel, append
from common import Common
branch_check_list = ["sprint", "stage-patch", "emergency1", "emergency"]
services2project = {
    "h5": "front-theory",
    "web": "front-theory",
    "trek": "front-goserver",
    "apps": "build",
    "global": "build",
    "bpmn-bridge": "q7link-services",
    "bpmn-server": "q7link-services",
    "batch": "q7link-services",
    "bpmn-reconclle": "q7link-services",
    "bankstmt": "q7link-services",
    "search": "q7link-services",
    "idgen": "q7link-services",
    "bankverify": "q7link-services",
}


class Task(Common):
    def __init__(self, crop, is_test=False):
        super().__init__()
        self.crop = crop
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
        if end != self.backend:
            applicant_id = user["applicant"][0]
            applicant_name = user["applicant"][1]
            return "none_version", applicant_id, applicant_name
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
    def new_branch_task(self, end, source, target, projects, **user):
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
            content = send_create_branch_msg(self.crop, source, target, projects,
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
    def check_version(self, branch):
        _name, _date = self.get_branch_date(branch)
        ret, msg = Shell('LuoLin', self.is_test).check_version(branch)
        logger.info(branch + ":" + msg)
        return ret, msg

    def clear_dirty_branch(self, user_id, branch_name):
        if self.is_trunk(branch_name):
            return
        ret, msg = Shell(user_id, self.is_test).clear_branch(branch_name)
        self.crop.send_text_msg(user_id, msg)

    # 发生清理脏分支通知
    def clear_dirty_branch_notice(self):
        # self.save_branch_pushed()
        clear_branch_msg = "您创建的分支【{}】超过三个月不存在提交记录，可能为脏分支，请确认是否需要删除？\n<a href=\"https://branch.linrol.cn/branch/clear?user_id={}&branch={}\">点击删除</a>\n无需删除请忽略"
        dirty_branches = self.get_dirty_branches()
        for branch, author in dirty_branches.items():
            username = hget("q7link-git-user", author)
            if username is None:
                continue
            user_id = self.name2userid(username)
            if user_id == "LuoLin":
                self.crop.send_text_msg(user_id, clear_branch_msg.format(branch, user_id, branch))
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
    def branch_correct(self, correct_user, branch, project):
        shell = Shell(correct_user, self.is_test, self.master, branch)
        params = "none other={}".format(project)
        _, msg = shell.build_package(params, "hotfix,all", True)
        logger.info("branch correct [{}] [{}] ret[{}]".format(branch, project, msg))
        duty_users, _ = self.get_duty_info(True)
        self.crop.send_text_msg(duty_users, msg)
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
    def send_mr_notify(self):
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
            self.crop.send_text_msg(assignee_user_id, mr_target_msg)
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
            self.crop.send_text_msg(author_userid, mr_source_msg)

    # 发送编译结果通知
    def send_build_notify(self, build_id, ret):
        user_id = hget("q7link-branch-build", build_id)
        if user_id is None:
            return
        ret_msg = "成功" if ret == "true" else "失败"
        build_msg = msg_content["build_ret"].format(build_id, ret_msg)
        self.crop.send_text_msg(user_id, build_msg)
        hdel("q7link-branch-build", build_id)

    # 解析并构建代码合并任务
    def build_merge_task(self, branches, services, clusters):
        tmp = set()
        for s in services:
            tmp.add(services2project.get(s, s))
        projects = list(tmp)
        rets = []
        duty_branches = self.get_duty_branches()
        for source_name in branches:
            if self.is_chinese(source_name):
                continue
            source_prefix, _ = self.get_branch_date(source_name)
            if len(duty_branches) > 0 and source_prefix not in duty_branches:
                continue
            is_sprint = source_prefix in ["sprint", "release"]
            cluster_str = ",".join(clusters)
            push_prod = append("q7link-cluster-release", source_name, cluster_str) > 8
            push_cluster_1 = "宁夏灰度集群1" in clusters
            clusters.discard("宁夏灰度集群1")
            push_cluster_0 = "宁夏灰度集群0" in clusters and len(clusters) == 1
            clusters.discard("宁夏灰度集群0")
            push_global = "宁夏生产global集群" in clusters and len(clusters) == 1
            clusters.discard("宁夏生产global集群")
            push_perform = 0 < len(clusters) < 6
            for p_name in projects:
                project = self.projects.get(p_name)
                if project is None:
                    rets.append("工程【{}】不存在".format(p_name))
                    continue
                end = project.getEnd()
                params = {
                    "is_sprint": is_sprint,
                    "source_release": self.backend == end and self.has_release(source_name),
                    "is_global": project.isGlobal(),
                    "cluster_global": push_global,
                    "cluster_0": push_cluster_0,
                    "cluster_1": push_cluster_1,
                    "cluster_perform": push_perform,
                    "cluster_prod":  push_prod
                }
                params_str = str(params)
                module = project.getModule()
                rules = self.get_merge_rules(end, module)
                for k, v in rules.items():
                    merge_params = k.split(">")
                    action = merge_params[0]
                    action_move = action == "move"
                    action_merge = action == "merge"
                    source = merge_params[1].replace("${source}", source_name)
                    target = merge_params[2]
                    rule_ret = eval(v, params)
                    if not rule_ret:
                        # rule_log = "project {} eval rule {}({}) by params({}) ret:{}".format(p_name, v, k, params_str, rule_ret)
                        # logger.warn(rule_log)
                        # ret.append("工程【{}】来源分支【{}】合并至目标分支【{}】不满足配置条件".format(p_name, source, target))
                        continue
                    if project.getBranch(source) is None:
                        rets.append("工程【{}】来源分支【{}】不存在".format(p_name, source))
                        continue
                    tmp_name = self.get_branch_created_source(end, source)
                    if tmp_name is not None:
                        target = target.replace("${target}", tmp_name)
                    if "$" in target:
                        rets.append("工程【{}】来源分支【{}】未知的创建信息".format(p_name, source))
                        continue
                    task_name = "{}_{}_{}_{}".format(p_name, source, target, action)
                    if task_name in rets:
                        continue
                    target_branch = project.getBranch(target)
                    if action_merge and target_branch is None:
                        rets.append("工程【{}】目标分支【{}】不存在".format(p_name, target))
                        continue
                    if action_move and target_branch is not None:
                        rets.append("工程【{}】目标分支【{}】已存在".format(p_name, target))
                        continue
                    if action_merge and project.checkMerge(source, target) and source != self.stage_global:
                        rets.append("工程【{}】来源分支【{}】已合并至目标分支【{}】".format(p_name, source, target))
                        continue
                    user_ids, _ = self.get_duty_info(self.is_test, end)
                    if action_move and target == self.stage_global:
                        p_name = "global"
                    if action_move and target == self.perform:
                        p_name = self.backend
                    self.send_branch_action(action, user_ids, source, target, p_name, cluster_str)
                    rets.append(task_name)
        return rets

    # 发现分支代码同步：当主干分支(stage,master)一致时且推送至所有集群时，主干分支自省同步
    def trigger_sync(self, user_id, projects, source, target):
        try:
            if self.is_sprint(source):
                return
            if self.is_trunk(source):
                return
            if not self.is_trunk(target):
                return
            for p_name in projects:
                project = self.projects.get(p_name)
                if project.isGlobal():
                    continue
                if not project.checkMerge(self.stage, self.master):
                    logger.info("differ from {} to {}".format(self.stage, self.master))
                    continue
                if not project.checkMerge(self.master, self.stage):
                    logger.info("differ from {} to {}".format(self.master, self.stage))
                    continue
                trunk_branch = self.stage if target == self.master else self.master
                self.send_branch_action("merge", user_id, target, trunk_branch, p_name, "全部租户集群")
        except Exception as err:
            logger.exception(err)

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
    def send_branch_action(self, action, user_ids, source, target, project, cluster_str):
        # 发送合并代码通知
        time.sleep(3)
        task_key = "branch_{}@{}".format(action, int(time.time()))
        if action == "merge":
            task_params = build_merge_branch_msg(source, target, project, cluster_str, task_key)
        elif action == "move":
            task_params = build_move_branch_msg(source, target, project, cluster_str, task_key)
        else:
            raise Exception("branch action error")
        # 发送应用任务消息并记录任务
        body = self.crop.send_template_card(user_ids, task_params)
        task_code = body.get("response_code")
        task_value = "{}#{}#{}#{}#{}".format(str(self.is_test), task_code, source, target, project)
        logger.info("write task[{}->{}]".format(task_key, task_value))
        save_user_task(task_key, task_value)
        return task_key

    def branch_seal(self, body):
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

    def front_data_pre(self, body):
        env = body.get("env")
        tenant_id = "tenant" + body.get("tenant_id")
        branch = body.get("branch")
        condition = body.get("condition")
        user_id = self.name2userid(body.get("user"))
        user_id_liming = self.name2userid('刘黎明')
        try:
            shell = Shell('LiMing', target_branch=branch)
            ret, result = shell.exec_data_pre('new', env, tenant_id, branch, condition, user_id_liming)
            if ret:
                self.crop.send_text_msg(user_id, result)
                self.crop.send_text_msg(user_id_liming, result)
            return result
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            return str(err)
