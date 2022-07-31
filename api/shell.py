import os
import sys
import subprocess
import time

from redisclient import add_mr, get_mr_ids, delete_mr
from MethodUtil import add_method
sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
from branch import utils
from dataPre import multi
from dataPre import uiconfig

def chdir_branch():
    os.chdir("../branch/")

def chdir_data_pre():
    os.chdir("../dataPre/")

class Shell(utils.ProjectInfo):
    def __init__(self, project_name):
        chdir_branch()
        self.project = utils.project_path().get(project_name)
        add_method(self.project)

    # 获取目标分支+当前人是否还存在未合并的mr分支
    def get_open_mr_branch(self, mr_key, branch):
        temp_branch = branch + str(int(time.time()))
        mr_ids = get_mr_ids(mr_key)
        if mr_ids is None:
            return None, temp_branch
        mr_list = self.project.getProject().mergerequests.list(state='opened', iids=mr_ids.split(","))
        if mr_list is not None and len(mr_list) > 0:
            return mr_list[0], mr_list[0].source_branch
        delete_mr(mr_key)
        return None, temp_branch

    def create_mr(self, mr_key, opened_mr, temp_branch, branch, title, assignee):
        cmd = 'cd {};git push origin {}'.format(self.project.getPath(), temp_branch)
        [ret, msg] = subprocess.getstatusoutput(cmd)
        if ret != 0:
            return False, msg
        if opened_mr is not None:
            return True , opened_mr.web_url
        mr = self.project.createMrRequest(temp_branch, branch, title, assignee)
        add_mr(mr_key, mr.web_url.rsplit("/",1)[1])
        return True, mr.web_url

    def exec_data_pre(self, from_user, data_type, env, tenant_id, branch, commit_user, condition_value):
        mr_key = from_user + env + tenant_id + branch
        opened_mr, temp_branch = self.get_open_mr_branch(mr_key, branch)
        try:
            # 仅当不存在待合并的分支才创建远程分支
            if opened_mr is None:
                self.project.createBranch(branch, temp_branch)
            #删除本地分支
            self.project.deleteLocalBranch(temp_branch)
            #在本地将新分支拉取出来
            self.project.checkout(temp_branch)
            condition = "name = '{}'".format(condition_value)
            chdir_data_pre()
            ret = None
            if data_type == 'new':
                ret = multi.pre_multi_list(env, tenant_id, temp_branch, commit_user, condition)
            if data_type == 'old':
                ret = uiconfig.pre_form(env, tenant_id, temp_branch, commit_user, condition)
            chdir_branch()
            if not ret:
                raise Exception("预制数据失败，请检查输出日志")
            return self.create_mr(mr_key, opened_mr, temp_branch, branch, '<数据预置>前端多列表方案预置', 'linrol')
        except Exception as err:
            self.project.deleteRemoteBranch(temp_branch)
            return False, err
        finally:
            self.project.checkout('master')
            self.project.deleteLocalBranch(temp_branch)