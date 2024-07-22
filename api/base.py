import re
import pymysql
import pymysql.cursors
import json
from request import post_form, put_form, get, post
from log import logger
from redisclient import get_branch_mapping, hget, hgetall, hget_key, hmset, get_version
from constant import msg_content, project_json


class Base:
    backend = "backend"
    front = "front"
    other = "other"
    stage = "stage"
    perform = "perform"
    master = "master"
    stage_global = "stage-global"
    date_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'
    rd_url = "http://10.0.144.51:5000"
    build_url = "http://ops.q7link.com:8000/qqdeploy/projectbuild/"
    web_hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=f28f65f5-c28d-46e5-8006-5f777f02dc71"
    backend_web_hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=6bc35c7b-c884-4707-98ba-722dae243d1f"
    check_version_web_hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=9b89b507-f2d4-4149-9e2f-5c6c8056313a"
    project_category = {}
    merge_rule = None
    category_mapping = {"global": ['framework', 'global-apps', 'global-apps-api'],
                        "apps": ['framework', 'enterprise', 'enterprise-apps', 'enterprise-apps-api']}

    # 获取分支前缀和时间
    def get_branch_date(self, branch):
        if re.search(self.date_regex, branch):
            date = re.search(self.date_regex, branch).group()
            name = branch.replace(date, "")
            return name, date
        return branch, None

    # 判断是否为主干分支
    def is_trunk(self, branch):
        return branch in [self.stage, self.perform, self.master]

    # 判断分支是否为sprint｜release
    def is_sprint(self, branch):
        source_prefix, _ = self.get_branch_date(branch)
        return source_prefix in ["sprint", "release"]

    # Git或企业微信用户ID转换中文名称
    @staticmethod
    def userid2name(user_id):
        if user_id is None:
            return None
        user_name = hget("q7link-git-user", user_id)
        if user_name is None:
            user_name = hget("wwcba5faed367cdeee", "{}-userinfo".format(user_id))
        return user_name

    # 用户名称转换企业微信ID
    def name2userid(self, user_name):
        try:
            if user_name is None:
                return None
            key = hget_key("wwcba5faed367cdeee", user_name)
            if key is not None:
                return key.replace("-userinfo", "")
            url = "{}/api/verify/duty/user_id?user_name={}"
            body = get(url.format(self.rd_url, user_name))
            return body.get("data")[0].get("user_id")
        except Exception as err:
            logger.error("name[{}] to userid error: {}".format(user_name, str(err)), exc_info=True)
            return None

    # 获取只读权限的值班人
    def get_readonly_duties(self):
        ids = []
        try:
            body = get("{}/api/verify/duty/users".format(self.rd_url))
            sqa_duties = body.get("data").get("sqa")
            # sqa|测试值班人（仅接收消息通知）
            for duty in sqa_duties:
                ids.append(duty.get("user_id"))
            test_duties = body.get("data").get("test")
            for duty in test_duties:
                ids.append(duty.get("user_id"))
        except Exception as err:
            logger.error("get readonly user error: {}".format(str(err)), exc_info=True)
        return ids

    # 获取值班人
    def get_duty_info(self, is_test, end=backend):
        if is_test:
            return "LuoLin", "罗林"
        else:
            data = get("{}/api/verify/duty/users".format(self.rd_url)).get("data")
            # body = {"data": {"backend": [{"user_id": "zhaojunlei", "user_name": "赵俊磊"}], "front": [{"user_id": "LiPan", "user_name": "李攀"}]}}
            data["openapi_qtms"] = data.get("openapi")
            data["openapi-doc"] = data.get("openapi")
            data["idps_front"] = data.get("idps")
            end_duties = data.get(end)
            user_ids = []
            user_names = []
            # 所属端值班人
            for duty in end_duties:
                user_ids.append(duty.get("user_id"))
                user_names.append(duty.get("user_name"))
            # 固定值班人
            fixed_users = hget("q7link_fixed_duty", end)
            if fixed_users is not None:
                user_ids.extend(fixed_users.split(","))
            # 只读值班人（仅接受消息，sqa）
            readonly_ids = self.get_readonly_duties()
            if len(readonly_ids) > 0:
                user_ids.extend(readonly_ids)
            return "|".join(user_ids), ",".join(user_names)

    # 获取值班目标分支集合
    @staticmethod
    def get_duty_targets():
        branches = set()
        try:
            mapping = get_branch_mapping()
            for bs in mapping.values():
                branches.update(bs.split(","))
        except Exception as err:
            logger.exception(err)
        return branches

    # 判断值班目标分支是否匹配来源分支
    def match_branch_mapping(self, source, target):
        prefix, _ = self.get_branch_date(target)
        mapping = get_branch_mapping()
        for k, v in mapping.items():
            if prefix not in v.split(","):
                continue
            if re.match("^{}$".format(k), source):
                return True
        return False

    # 判断值班分支
    def is_duty(self, branch):
        mapping = get_branch_mapping()
        for k, v in mapping.items():
            match_source = re.match("^{}$".format(k), branch)
            prefix, _ = self.get_branch_date(branch)
            if match_source or prefix in v.split(","):
                return True
        return False

    # 获取分支合并策略
    def get_merge_rules(self, end, module):
        try:
            if self.merge_rule is None:
                self.merge_rule = hgetall("q7link-branch-merge-rule")
            for k, v in self.merge_rule.items():
                if k in [end, module]:
                    return json.loads(v)
            return {}
        except Exception as err:
            logger.exception(err)
            return {}

    # 删除本地分支
    def delete_branch(self, branch, projects):
        if branch is None:
            return
        if len(projects) < 1:
            return
        if self.is_trunk(branch):
            return
        for project in projects:
            project.deleteLocalBranch(branch)

    @staticmethod
    def is_chinese(word):
        for ch in word:
            if '\u4e00' <= ch <= '\u9fff':
                return True
        return False

    # 获取项目所属端
    def get_project_end(self, projects):
        ends = set()
        for end, modules in project_json.items():
            if end in projects:
                ends.add(end)
            for module, ps in modules.items():
                if module in projects:
                    ends.add(end)
                for p in ps.keys():
                    if p in projects:
                        ends.add(end)
        if len(ends) < 1:
            return self.backend
        if len(ends) > 1:
            raise Exception("工程模块的分支负责人存在多个，请分开发起请求")
        return list(ends)[0]

    # 触发ops编译
    def ops_build(self, branch, skip=False, project=None, user_name=None):
        try:
            if skip:
                return
            caller = "研发助手"
            if user_name is not None:
                caller = "{}-研发助手".format(user_name)
            params = {"branch": branch, "byCaller": caller}
            if project is not None:
                params["projects"] = project
            res = post_form(self.build_url, params)
            build_id = res.get("data").get("taskid")
            hmset("q7link-branch-build", {build_id: user_name})
            return build_id
        except Exception as err:
            logger.exception(err)
            return "-1"

    def ops_ticket_status(self, ticket_id):
        try:
            params = {"ticket_id": ticket_id}
            res = put_form(self.build_url, params)
            return res
        except Exception as err:
            logger.exception(err)
            return "-1"

    def save_branch_created(self, user_id, source, target, projects):
        excludes = [self.stage_global]
        if source in excludes:
            return
        end = self.get_project_end(projects)
        created_value = "{}#{}#{}".format(source, user_id, ",".join(projects))
        created_mapping = {end + "@" + target: created_value}
        hmset('q7link-branch-created', created_mapping)

    @staticmethod
    def get_branch_created_source(end, target):
        key = end + "@" + target
        created_value = hget("q7link-branch-created", key)
        if created_value is None:
            return None
        return created_value.split("#")[0]

    # 发送群消息代码合并通知
    def send_mr_group_notify(self, source, target, modules, ret, user, end):
        try:
            if not self.is_duty(target):
                return True
            is_backend = end == self.backend
            ret_msg = "成功" if ret else "失败（分支代码存在冲突需手动合并）"
            content_template = msg_content["merge_branch_result"]
            module_str = "apps,global" if is_backend else ",".join(modules)
            content = content_template.format(source, target, module_str, ret_msg, user)
            msg = {"msgtype": "text", "text": {"content": content}}
            post(self.web_hook, msg)
            if is_backend:
                post(self.backend_web_hook, msg)
            return True
        except Exception as err:
            logger.exception(err)
            return False

    # 发送群消息版本号检查通知
    @staticmethod
    def send_msg_group_notify(web_hook, ret, msg):
        if ret:
            return
        msg = {"msgtype": "text", "text": {"content": msg}}
        post(web_hook, msg)

    # 代码合并后回调通知rd平台
    def notify_rd(self, target, merge_msg):
        try:
            is_global = "identity" in merge_msg or "reconcile" in merge_msg
            if not is_global:
                return True
            params = {"branch": target, "projects": ["backend/global"]}
            url = "{}/api/verify/dev/branch-merge"
            post(url.format(self.rd_url), params)
        except Exception as err:
            logger.exception(err)
            return False

    # 保存特性分支信息
    @staticmethod
    def save_branch_feature(target, source, version, leader_user):
        value = "{}@{}@{}".format(source, version, leader_user)
        hmset("q7link-branch-feature", {target: value})

    # 获取特性分支信息
    @staticmethod
    def get_branch_feature(target_branch):
        return hget("q7link-branch-feature", target_branch)

    # 获取校验升级的版本号信息
    @staticmethod
    def get_upgrade_version():
        return get_version()

    # 禅道sql查询
    @staticmethod
    def zt_fetchone(sql):
        try:
            db = pymysql.connect(host="pro-qiqizentao-202302011450-slave.clrq7smojqgq.rds.cn-northwest-1.amazonaws.com.cn",
                                 user="dev",
                                 password="Qqrddev666%",
                                 port=3306,
                                 database="zentao")
            cursor = db.cursor(pymysql.cursors.DictCursor)
            # 执行SQL语句
            cursor.execute(sql)
            # 获取所有记录列表
            results = cursor.fetchone()
            # 关闭数据库连接
            db.close()
            return results
        except Exception as err:
            logger.exception(err)
            return None
