import re
from request import post_form, get
from log import logger
from redisclient import get_branch_mapping, hget, hmset
date_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'
rd_url = "http://10.0.144.51:5000"


class Base:
    # 获取分支前缀和时间
    def get_branch_date(self, branch):
        if re.search(date_regex, branch):
            date = re.search(date_regex, branch).group()
            name = branch.replace(date, "")
            return name, date
        return branch, None

    # 用户名称转换企业微信ID
    def name2userid(self, user_name):
        try:
            if user_name is None:
                return None
            url = "{}/api/verify/duty/user_id?user_name={}"
            body = get(url.format(rd_url, user_name))
            return body.get("data")[0].get("user_id")
        except Exception as err:
            logger.error("name2userid error: {}".format(str(err)))
            return None

    # 获取值班人
    def get_duty_info(self, is_test, end="backend"):
        if is_test:
            return "LuoLin", "罗林"
        else:
            fixed_userid = hget("q7link_fixed_duty", end).split(",")
            body = get("{}/api/verify/duty/users".format(rd_url))
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
        except Exception as e:
            logger.error(e)
        return branches

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
        except Exception as e:
            logger.error(e)
            return "-1"

    def save_branch_created(self, user_id, source, target, projects):
        excludes = ["stage-global"]
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
