import os
import sys
import subprocess
from base import Base
from log import logger
sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/data/backend/branch-manage")
from branch import utils
date_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'


class Common(Base):
    def __init__(self):
        self.chdir_branch()
        self.utils = utils
        self.front_projects = utils.project_path(["front"])
        self.projects = {**utils.project_path(), **self.front_projects}
        self.project_build = self.projects.get('build')
        self.project_init_data = self.projects.get('init-data')

    def exec(self, command, throw=False, level_info=True):
        [ret, msg] = subprocess.getstatusoutput(command)
        if throw and ret != 0:
            logger.error("exec[{}] ret[{}]".format(command, msg))
            raise Exception(str(msg))
        if level_info:
            logger.info("exec[{}] ret[{}]".format(command, msg))
        return [ret == 0, msg]

    def chdir_branch(self):
        os.chdir("../branch/")

    def chdir_data_pre(self):
        os.chdir("../dataPre/")

    # 是否首次创建分支
    def init_create_branch(self, branch):
        return self.project_build.getBranch(branch) is None

    # 获取清空build脚本的参数
    def get_clear_build_params(self, branch):
        if self.init_create_branch(branch):
            return "true"
        else:
            return "false"

    # 切换本地分支
    def checkout_branch(self, branch, end="backend"):
        cmd = 'cd ../branch;python3 checkout.py {} {}'.format(end, branch)
        return self.exec(cmd, True, False)

    # 删除分支
    def clear_branch(self, branch):
        try:
            cmd = 'cd ../branch;python3 checkanddeleted.py {} none'.format(branch)
            return self.exec(cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 获取远端文件
    def git_file(self, project, branch, file_path):
        f = project.getProject().files.get(file_path=file_path, ref=branch)
        return f

    # 清空前端升级脚本
    def clear_front_upgrade(self, projects, branch, path):
        try:
            name = "front-goserver"
            if name not in projects:
                raise Exception("当前工程不涉及升级接口文件")
            project = self.projects.get(name)
            file = self.git_file(project, branch, path)
            if file is None:
                raise Exception("升级接口文件不存在")
            message = "{}-task-0000-{}".format(branch, "清空升级接口")
            file.content = ''
            file.save(branch=branch, commit_message=message)
            return True, "\n工程【{}】清空升级接口完成".format(name)
        except Exception as err:
            return False, str(err)

    # 保护分支
    def protect_branch(self, branch, protect, projects=None):
        if projects is None:
            projects = []
        elif "all" in projects:
            projects.extend(["apps", "global", "platform"])
            projects.remove("all")
        elif "apps" in projects:
            projects.extend(["platform", "init-data"])
        elif "global" in projects:
            projects.extend(["platform", "init-data"])
        try:
            cmd = "cd ../branch;python3 protectBranch.py {} {} {}".format(branch, protect, " ".join(projects))
            return self.exec(cmd, level_info=False)
        except Exception as err:
            return False, str(err)

    # 保护分支(直接调用git)
    def protect_git_branch(self, branch, project, access):
        try:
            tmp_msg = ""
            if access == "hotfix":
                mr_access = utils.MAINTAINER_ACCESS
                push_access = utils.VISIBILITY_PRIVATE
                tmp_msg = "取消"
            elif access == "none":
                mr_access = utils.VISIBILITY_PRIVATE
                push_access = utils.VISIBILITY_PRIVATE
            else:
                raise Exception("分支保护不支持的权限参数")
            _p_list = self.projects.get("parent").getGl().projects.list(search=project)
            _p_b = _p_list.get(0).protectedbranches.get(branch)
            _p_b.delete()
            _p_b.create({
                'name': branch,
                'merge_access_level': mr_access,
                'push_access_level': push_access
            })
            return True, "工程【{}】分支【{}】{}保护成功".format(project, branch, tmp_msg)
        except Exception as err:
            logger.exception(err)
            return False, str(err)

    # 获取合并代码的分支
    def get_merge_branch(self, branches, clusters, project):
        duty_branches = self.get_duty_branches()
        branch_merge = {}
        is_backend = self.get_project_end([project]) == "backend"
        error = []
        for branch in branches:
            if self.is_chinese(branch):
                continue
            branch_prefix, _ = self.get_branch_date(branch)
            if len(duty_branches) > 0 and branch_prefix not in duty_branches:
                continue
            is_sprint = "sprint" in branch
            push_stage0 = "集群0" in clusters
            if is_sprint and push_stage0:
                # 班车推灰度0环境，后端stage-global合并至sprint，前端跳过
                if not is_backend:
                    continue
                branch = "stage-global"
            prod_clusters = {"集群3", "集群4", "集群5", "集群6", "集群7"}
            push_prod = len(set(clusters).intersection(prod_clusters)) > 2
            git_project = self.projects.get(project)
            source_branch = git_project.getBranch(branch)
            if is_sprint and source_branch is None and push_prod:
                # 班车推生产环境，stage合并至master
                branch_merge["stage"] = "master"
                continue
            if source_branch is None:
                error.append("分支【{}】不存在".format(branch))
                continue
            target = self.get_branch_created_source(branch)
            if target is None:
                error.append("分支【{}】未知的目标分支".format(branch))
                continue
            if git_project.getBranch(target) is None:
                error.append("分支【{}】不存在".format(branch))
                continue
            is_merge = git_project.checkMerge(branch, target)
            if (not is_backend) and is_merge:
                error.append("工程【{}】分支【{}】已合并至【{}】".format(project, branch, target))
                continue
            branch_merge[branch] = target
        if len(branch_merge) < 1:
            raise Exception("解析合并分支信息失败: {}".format(";".join(error)))
        if len(branch_merge) > 1:
            raise Exception("解析合并分支信息不唯一: {}".format(branch_merge))
        logger.info("解析合并分支日志内容: {}".format(";".join(error)))
        for k, v in branch_merge.items():
            return k, v



