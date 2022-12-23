import re
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

    # 获取值班人
    def get_duty_info(self, is_test, end="backend"):
        if is_test:
            return "LuoLin", "罗林"
        else:
            fixed_userid = hget("q7link_fixed_duty", end).split(",")
            body = get("{}/api/verify/duty/users".format(self.rd_url))
            role_duty_info = body.get("data").get(end)
            duty_user_ids = []
            duty_user_names = []
            for duty in role_duty_info:
                duty_user_ids.append(duty.get("user_id"))
                duty_user_names.append(duty.get("user_name"))
            if len(fixed_userid) > 0:
                duty_user_ids.extend(fixed_userid)
            return "|".join(duty_user_ids), ",".join(duty_user_names)

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
            build_url = "http://ops.q7link.com:8000/qqdeploy/projectbuild/"
            if skip:
                return
            caller = "值班助手"
            if call_name is not None:
                caller = "{}-值班助手".format(call_name)
            params = {"branch": branch, "byCaller": caller}
            if project is not None:
                params["projects"] = project
            res = post_form(build_url, params)
            return res.get("data").get("taskid")
        except Exception as err:
            logger.exception(err)
            return "-1"

    def save_branch_created(self, user_id, source, target, projects):
        excludes = [self.stage_global]
        if source in excludes:
            return
        created_value = "{}#{}#{}".format(source, user_id, ",".join(projects))
        created_mapping = {target: created_value}
        hmset('q7link-branch-created', created_mapping)

    def get_branch_created_source(self, target):
        created_value = hget("q7link-branch-created", target)
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
        except Exception as err:
            logger.exception(err)
            return "-1"

