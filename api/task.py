import random
import string
import time
import re
from datetime import datetime, date, timedelta
from log import logger
from shell import Shell
from wxmessage import send_create_branch_msg, build_merge_branch_msg, build_move_branch_msg, msg_content
from redisclient import save_user_task, get_branch_mapping, hmset, hget, hgetall, hdel, append
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
    "search-710": "q7link-services",
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

    def cal_new_branch_version(self, source, target, end, user):
        target_name, _ = self.get_branch_date(target)
        if target_name in self.get_duty_targets():
            # 目标分支是值班分支
            self.assert_duty(end, source, target)
            return None
        applicant_id = user["applicant"][0]
        applicant_name = user["applicant"][1]
        if end != self.backend:
            user["watchman"] = (applicant_id, applicant_name)
            return "none_version"
        feature_info = self.get_branch_feature(target)
        if feature_info is None:
            sql = "select * from zt_project where code = '{}' and type='sprint'".format(target)
            zt_project_info = self.zt_fetchone(sql)
            if zt_project_info is None:
                self.raise_branch_init(source, target, applicant_name)
            app = zt_project_info.get("app")
            pm = zt_project_info.get("PM")
            account = (pm if (app is None or app.isspace()) else app).replace(",", "")
            sql = "select * from zt_user where account = '{}'".format(account)
            zt_user_info = self.zt_fetchone(sql)
            if zt_user_info is None:
                self.raise_branch_init(source, target, applicant_name)
            leader_user = zt_user_info.get("realname", None)
            version = self.gen_feature_version(source)
            self.save_branch_feature(target, source, version, leader_user)
            user["watchman"] = (self.name2userid(leader_user), leader_user)
            return version
        _source = feature_info.split("@")[0]
        if _source != source:
            logger.info("Waring: 特性分支初始化时来源分支为【{}】".format(_source))
            # raise Exception("Waring: 特性分支创建时来源分支为【{}】".format(source))
        version = feature_info.split("@")[1]
        approve = feature_info.split("@")[2]
        user["watchman"] = (self.name2userid(approve), approve)
        return version

    def filter_project(self, target, projects):
        project_str = ",".join(projects)
        projects = list(filter(lambda name: self.get_project_branch(name, target) is None, projects))
        if len(projects) < 1:
            raise Exception("ERROR: \n" + "工程【{}】目标分支【{}】已存在!!!".format(project_str, target))
        return projects

    def gen_feature_version(self, branch):
        framework_version = self.get_branch_version(branch).get("framework")
        prefix = re.match("[0-9]+[.][0-9]+[.][0-9]+", framework_version).group()
        random_str = ''.join(random.sample(string.ascii_letters, 6))
        return "{}.{}-SNAPSHOT".format(prefix, random_str)

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

    # 断言值班分支的来源是否正确，目标分支的上线日期等
    def assert_duty(self, end, source, target):
        if not self.match_branch_mapping(source, target):
            raise Exception("不受支持的来源分支，请检查或联系管理者配置分支映射关系")
        _, target_date = self.get_branch_date(target)
        week_later = (datetime.now() + timedelta(days=-7)).strftime("%Y%m%d")
        if int(week_later) > int(target_date):
            raise Exception("目标分支的上线日期过小，请检查分支名称日期")
        if self.backend == end and self.is_protected(target):
            raise Exception("目标分支权限被保护，请联系值班确认是否合并代码中或处理权限")

    # 提示用户进行分支初始化操作
    def raise_branch_init(self, source, target, user_name):
        tips = "目标分支为特性分支时，需按以下格式初始化后可操作(可修改分支版本号，负责人等信息)：" + \
               "\n====================" + \
               "\n操　　作：初始化特性分支" + \
               "\n来源分支：" + source + \
               "\n目标分支：" + target + \
               "\n分支版本号：{}" + \
               "\n分支负责人：" + user_name
        raise Exception(tips.format(self.gen_feature_version(source)))

    # 创建拉分支的任务
    def new_branch_task(self, end, source, target, projects, **user):
        projects = self.filter_project(target, projects)
        version = self.cal_new_branch_version(source, target, end, user)
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
    def check_version(self, branch, author_id):
        _name, _date = self.get_branch_date(branch)
        no_conflict, msg = Shell(author_id, self.is_test).check_version(branch)
        if no_conflict:
            return None
        # 发送冲突提醒
        unknown_user = author_id in ["backend-ci"]
        user_name = self.get_branch_creator(branch) if unknown_user else self.userid2name(author_id)
        logger.info("check version notify user [{}.{}]".format(author_id, user_name))
        self.crop.send_text_msg(self.name2userid(user_name), msg)
        return no_conflict, msg

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
        for branch, author_id in dirty_branches.items():
            author_name = self.userid2name(author_id)
            if author_name is None:
                continue
            user_id = self.name2userid(author_name)
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
        _, msg = shell.package("build", params, "hotfix,all", True)
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
        before_hours = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
        gl = self.get_project('parent').getGl()
        # 发送待合并通知
        opened_mrs = gl.mergerequests.list(state='opened', scope="all", created_after=before_hours)
        for mr in opened_mrs:
            if mr.assignee is None:
                continue
            mr_key = "opened_" + mr.web_url
            if hget("q7link-branch-merge", mr_key) is not None:
                continue
            author_id = mr.author.get("username")
            git_assignee_id = mr.assignee.get("username")
            if author_id == git_assignee_id:
                continue
            author_name = self.userid2name(author_id)
            if author_name is None:
                author_name = author_id
            assignee_name = self.userid2name(git_assignee_id)
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
            self.crop.send_text_msg(assignee_user_id, mr_target_msg)
            hmset("q7link-branch-merge", {mr_key: assignee_name})

        # 发送已合并通知
        merged_mrs = gl.mergerequests.list(state='merged', scope="all", updated_after=before_hours)
        for mr in merged_mrs:
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
            merged_username = self.userid2name(merged_userid)
            if merged_username is None:
                merged_username = merged_userid
            author_name = mr.title.replace(data_pre_str, "") if is_data_pre else self.userid2name(author_id)
            if not author_name:
                logger.error("author user [{}] not found".format(author_id))
                continue
            author_userid = self.name2userid(author_name)
            project_full = mr.references.get("full").split("!")[0]
            _, project = project_full.rsplit("/", 1)
            mr_source_msg = msg_content["mr_source"].format(mr.web_url, project, merged_username)
            if project in self.projects.keys() and project not in ["build"] and self.projects.get(project).getEnd() == self.backend:
                build_id = self.ops_build(mr.target_branch, False, project_full, author_name)
                mr_source_msg += "\n已触发独立编译任务ID:{}，请自行关注编译结果".format(build_id)
            hmset("q7link-branch-merge", {mr_key: author_userid})
            self.crop.send_text_msg(author_userid, mr_source_msg)

    # 发送编译结果通知
    def send_build_notify(self, build_id, ret):
        user_name = hget("q7link-branch-build", build_id)
        if user_name is None:
            return
        ret_msg = "成功" if ret == "true" else "失败"
        build_msg = msg_content["build_ret"].format(build_id, ret_msg)
        user_id = self.name2userid(user_name)
        self.crop.send_text_msg(user_id, build_msg)
        hdel("q7link-branch-build", build_id)

    # 解析并构建代码合并任务
    def build_merge_task(self, branches, services, clusters):
        tmp = set()
        for s in services:
            tmp.add(services2project.get(s, s))
        projects = list(tmp)
        rets = []
        duty_branches = self.get_duty_targets()
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
                    if self.backend == end and action_move and target == self.stage_global:
                        p_name = "global"
                    if self.backend == end and action_move and target == self.perform:
                        p_name = self.backend
                    self.send_branch_action(action, user_ids, source, target, p_name, cluster_str)
                    rets.append(task_name)
        return rets

    # 发现分支代码同步：当主干分支(stage,master)一致时且推送至所有集群时，主干分支自省同步
    def merge_trigger(self, user_id, source, target, projects, cluster_str):
        try:
            if cluster_str is None:
                return
            if self.is_sprint(source) or self.is_trunk(source):
                # 来源分支是班车或者主干时，则跳过
                return
            if not self.is_trunk(target):
                # 目标分支非主干分支，则跳过
                return
            cluster_count = len(cluster_str.split(","))
            push_prod = 8 < cluster_count
            push_stage = "宁夏灰度集群1" in cluster_str
            push_perform = 2 < cluster_count < 9
            if target != self.stage and push_stage:
                trunk_branch = self.stage
            elif target == self.stage and push_perform:
                trunk_branch = self.perform
            elif target == self.stage and push_prod:
                trunk_branch = self.master
            else:
                return
            logger.info("branch trigger sync from {} to {}".format(target, trunk_branch))
            for p_name in projects:
                project = self.projects.get(p_name)
                if project.isGlobal():
                    continue
                if project.getBranch(trunk_branch) is None:
                    continue
                self.send_branch_action("merge", user_id, target, trunk_branch, p_name, cluster_str)
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
        task_value = "{}#{}#{}#{}#{}#{}".format(str(self.is_test), task_code, source, target, project, cluster_str)
        logger.info("write task[{}->{}]".format(task_key, task_value))
        save_user_task(task_key, task_value)
        return task_key

    def branch_seal(self, body):
        response = {}
        user_id, branch, projects, is_seal, clear_cache = body.get("user_id"), body.get("branch"), body.get("projects"), body.get("is_seal") == "true", body.get("clear_cache", 'false') == "true"
        shell = Shell(user_id, self.is_test, self.master, branch)
        access = "none" if is_seal else "hotfix"
        for project in projects:
            is_backend = project in ["apps", "global"]
            if project not in self.projects.keys() and not is_backend:
                ret, msg = self.protect_git_branch(branch, project, access)
            else:
                ret, msg = self.protect_branch(branch, access, [project])
            response[project] = {"ret": ret, "msg": msg}
        modules = list(set(projects).intersection({"apps", "global"}))
        if len(modules) < 1:
            return response
        # 后端封板/取消封板
        if len(modules) > 1:
            modules = ["all"]
        front_version = body.get("front_version", "").strip()
        if len(front_version) > 0:
            modules.append("front-apps=reimburse:{}".format(front_version))
        if clear_cache:
            cache_version = time.strftime("%Y%m%d%H%M")
            modules.append("cache=local:{}".format(cache_version))
        if is_seal and len(modules) > 0:
            # 后端封版，模块包含apps，global则构建发布包
            protect = access + "," + modules[0]
            action = "destroy" if body.get("delete_jar", 'false') == "true" else "build"
            is_build = body.get("is_build", "") == 'true'
            shell.package(action, " ".join(modules), protect, is_build)
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

    def app_update(self, name, notify, notify_msg):
        to_user_set = set()
        tasks = hgetall("q7link-user-task")
        for k, v in tasks.items():
            vs = v.split("#")
            if len(vs) < 3:
                continue
            user_id = v.split("#")[2]
            if user_id in to_user_set:
                continue
            if self.crop.get("{}-userinfo".format(user_id)) is None:
                continue
            to_user_set.add(user_id)
        to_user_ids = "|".join(list(to_user_set))
        self.crop.agent_update(name)
        if not notify:
            return
        self.crop.send_text_msg(to_user_ids, notify_msg)
