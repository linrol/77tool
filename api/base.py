import re
import pymysql
import pymysql.cursors
from request import post_form, get, post
from log import logger
from redisclient import get_branch_mapping, hget, hmset
from wxmessage import msg_content


class Base:
    stage = "stage"
    master = "master"
    stage_global = "stage-global"
    date_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'
    rd_url = "http://10.0.144.51:5000"
    build_url = "http://ops.q7link.com:8000/qqdeploy/projectbuild/"
    web_hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=f28f65f5-c28d-46e5-8006-5f777f02dc71"
    backend_web_hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=6bc35c7b-c884-4707-98ba-722dae243d1f"
    project_category = {}
    category_mapping = {"global": ['framework', 'global-apps', 'global-apps-api'],
                        "apps": ['framework', 'enterprise', 'enterprise-apps', 'enterprise-apps-api']}

    # 获取分支前缀和时间
    def get_branch_date(self, branch):
        if re.search(self.date_regex, branch):
            date = re.search(self.date_regex, branch).group()
            name = branch.replace(date, "")
            return name, date
        return branch, None

    # 用户名称转换企业微信ID
    def name2userid(self, user_name):
        try:
            if user_name is None:
                return None
            url = "{}/api/verify/duty/user_id?user_name={}"
            body = get(url.format(self.rd_url, user_name))
            return body.get("data")[0].get("user_id")
        except Exception as err:
            logger.error("name2user error: {}".format(str(err)), exc_info=True)
            return None

    # 获取只读权限的值班人
    def get_readonly_duties(self):
        ids = []
        try:
            body = get("{}/api/verify/duty/users".format(self.rd_url))
            sqa_duties = body.get("data").get("sqa")
            # sqa值班人（仅接受消息）
            for duty in sqa_duties:
                ids.append(duty.get("user_id"))
        except Exception as err:
            logger.error("get readonly user error: {}".format(str(err)), exc_info=True)
        return ids

    # 获取值班人
    def get_duty_info(self, is_test, end="backend"):
        if is_test:
            return "LuoLin", "罗林"
        else:
            body = get("{}/api/verify/duty/users".format(self.rd_url))
            end_duties = body.get("data").get(end)
            user_ids = []
            user_names = []
            # 所属端值班人
            for duty in end_duties:
                user_ids.append(duty.get("user_id"))
                user_names.append(duty.get("user_name"))
            # 固定值班人
            fixed_userid = hget("q7link_fixed_duty", end).split(",")
            if len(fixed_userid) > 0:
                user_ids.extend(fixed_userid)
            # 只读值班人（仅接受消息，sqa）
            readonly_ids = self.get_readonly_duties()
            if len(readonly_ids) > 0:
                user_ids.extend(readonly_ids)
            return "|".join(user_ids), ",".join(user_names)

    # 获取值班目标分支集合
    def get_duty_branches(self):
        branches = set()
        try:
            mapping = get_branch_mapping()
            for bs in mapping.values():
                branches.update(bs.split(","))
        except Exception as err:
            logger.exception(err)
        return branches

    # 判断是否为主干分支
    def is_trunk(self, branch):
        return branch in [self.stage, self.master]

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

    def is_chinese(self, word):
        for ch in word:
            if '\u4e00' <= ch <= '\u9fff':
                return True
        return False

    # 获取项目所属端
    def get_project_end(self, projects):
        front_projects = {"front-theory", "front-goserver"}
        intersection = set(projects).intersection(front_projects)
        if len(intersection) > 0:
            return "front"
        else:
            return "backend"

    # 触发ops编译
    def ops_build(self, branch, skip=False, project=None, call_name=None):
        try:
            if skip:
                return
            caller = "值班助手"
            if call_name is not None:
                caller = "{}-值班助手".format(call_name)
            params = {"branch": branch, "byCaller": caller}
            if project is not None:
                params["projects"] = project
            res = post_form(self.build_url, params)
            return res.get("data").get("taskid")
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

    def get_branch_created_source(self, end, target):
        key = end + "@" + target
        created_value = hget("q7link-branch-created", key)
        if created_value is None:
            return None
        return created_value.split("#")[0]

    # 发送群消息通知
    def send_group_notify(self, source, target, modules, ret, user, end):
        try:
            is_backend = end == "backend"
            ret_msg = "成功" if ret else "失败（分支代码存在冲突需手动合并）"
            content_template = msg_content["merge_branch_result"]
            module_str = "apps,global" if is_backend else ",".join(modules)
            content = content_template.format(source, target, module_str,
                                              ret_msg, user)
            msg = {"msgtype": "text", "text": {"content": content}}
            post(self.web_hook, msg)
            if is_backend:
                post(self.backend_web_hook, msg)
            return True
        except Exception as err:
            logger.exception(err)
            return False

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
    def save_branch_feature(self, target, source, version, leader_user):
        value = "{}@{}@{}".format(source, version, leader_user)
        hmset("q7link-branch-feature", {target: value})

    # 禅道sql查询
    def zt_fetchone(self, sql):
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



