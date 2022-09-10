import os
import sys
import subprocess
import time

from concurrent.futures import ThreadPoolExecutor

from redisclient import add_mr, get_mr_ids, delete_mr
from MethodUtil import add_method
from log import logger
from redisclient import redisClient
from redislock import RedisLock
from request import post_form
sys.path.append("/Users/linrol/work/sourcecode/qiqi/backend/branch-manage")
sys.path.append("/root/data/sourcecode/qiqi/backend/branch-manage")
from branch import utils

executor = ThreadPoolExecutor()

def chdir_branch():
    os.chdir("../branch/")

def chdir_data_pre():
    os.chdir("../dataPre/")

class Shell(utils.ProjectInfo):
    def __init__(self, user_id, is_test=False, source_branch=None, target_branch=None):
        chdir_branch()
        self.user_id = user_id
        self.is_test = is_test
        self.projects = utils.project_path()
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.project_init_data = self.project = self.projects.get('init-data')
        self.project_build = self.projects.get('build')
        add_method(self.project_init_data)
        self.lock = RedisLock(redisClient.get_connection())
        self.lock_value = None
        # self.rest_branch_env()

    def init_branch(self):
        return self.project_build.getBranch(self.target_branch) is None

    # 获取目标分支+当前人是否还存在未合并的mr分支
    def get_open_mr_branch(self, mr_key, branch):
        temp_branch = branch + str(int(time.time()))
        mr_ids = get_mr_ids(mr_key)
        if mr_ids is None:
            return None, temp_branch
        mr_list = self.project_init_data.getProject().mergerequests.list(state='opened', iids=mr_ids.split(","))
        if mr_list is not None and len(mr_list) > 0:
            return mr_list[0], mr_list[0].source_branch
        delete_mr(mr_key)
        return None, temp_branch

    def create_mr(self, mr_key, opened_mr, temp_branch, branch, title, assignee):
        cmd = 'cd {};git push origin {}'.format(self.project_init_data.getPath(), temp_branch)
        [ret, msg] = subprocess.getstatusoutput(cmd)
        if ret != 0:
            return False, msg
        if opened_mr is not None:
            return True, opened_mr.web_url
        mr = self.project_init_data.createMrRequest(temp_branch, branch, title, assignee)
        add_mr(mr_key, mr.web_url.rsplit("/", 1)[1])
        return True, mr.web_url

    def exec_data_pre(self, data_type, env, tenant_id, target_branch, condition_value, mr_user):
        mr_key = self.user_id + env + tenant_id + self.target_branch
        opened_mr, temp_branch = self.get_open_mr_branch(mr_key, self.target_branch)
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            # 仅当不存在待合并的分支才创建远程分支
            if opened_mr is None:
                self.project_init_data.createBranch(self.target_branch, temp_branch)
            #删除本地分支
            self.project_init_data.deleteLocalBranch(temp_branch)
            #在本地将新分支拉取出来
            self.project_init_data.checkout(temp_branch)
            chdir_data_pre()
            ret = None
            msg = None
            if data_type == 'new':
                cmd = 'cd ../dataPre;python3 multi.py {} {} {} {} {}'.format(env, tenant_id, temp_branch, self.user_id, condition_value)
                [ret, msg] = subprocess.getstatusoutput(cmd)
            if data_type == 'old':
                cmd = 'cd ../dataPre;python3 uiconfig.py {} {} {} {} {}'.format(env, tenant_id, temp_branch, self.user_id, condition_value)
                [ret, msg] = subprocess.getstatusoutput(cmd)
            chdir_branch()
            if ret != 0:
                raise Exception(msg + "\n预制失败，请检查输出日志")
            mr_title = '<数据预置>前端多列表方案预置-{}'.format(self.user_id)
            return self.create_mr(mr_key, opened_mr, temp_branch, self.target_branch, mr_title, mr_user)
        except Exception as err:
            self.project_init_data.deleteRemoteBranch(temp_branch)
            return False, str(err)
        finally:
            self.project_init_data.deleteLocalBranch(temp_branch)
            executor.submit(self.rest_branch_env)

    # 创建分支
    def create_branch(self, update_project_names, project_names):
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            init_branch = self.init_branch()
            [ret, checkout_msg] = self.checkout_branch(self.source_branch)
            if ret != 0:
                return False, checkout_msg
            cmd = 'cd ../branch;python3 createBranch.py {} {} {}'.format(self.source_branch, self.target_branch, " ".join(project_names))
            logger.info("create_branch[{}]".format(cmd))
            [ret, create_msg] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                return False, create_msg
            cmd = 'cd ../branch;python3 genVersion.py {} {} {}'.format(self.source_branch, self.target_branch + ".force", " ".join(update_project_names))
            logger.info("create_branch[{}]".format(cmd))
            [ret, update_version_msg] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                return False, update_version_msg
            cmd = 'cd ../branch;python3 genVersion.py {} {} {}'.format(self.source_branch, self.target_branch, " ".join(project_names))
            logger.info("create_branch[{}]".format(cmd))
            [ret, gen_version_msg] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                return False, gen_version_msg
            cmd = 'cd ../branch;python3 changeVersion.py {}'.format(self.target_branch)
            if init_branch:
                cmd += " true"
            logger.info("create_branch[{}]".format(cmd))
            [ret, change_version_msg] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                return False, change_version_msg
            self.commit_and_push(self.target_branch, 'hotfix')
            try:
                if not self.is_test:
                    params = {"branch": self.target_branch, "byCaller": "值班助手"}
                    post_form("http://ops.q7link.com:8000/qqdeploy/projectbuild/", params)
            except Exception as e:
                logger.error(e)
            return True, (create_msg + change_version_msg).replace("\n", "").replace("工程", "\n工程")
        except Exception as err:
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    def check_version(self, branch_str):
        try:
            user_id = self.user_id
            cmd = 'cd ../branch;python3 checkVersion.py -t compare -b {}'.format(branch_str)
            [ret, check_version_msg] = subprocess.getstatusoutput(cmd)
            return ret == 0, check_version_msg
        except Exception as err:
            return False, str(err)

    def build_package(self, group, is_build):
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            [ret, checkout_msg] = self.checkout_branch(self.target_branch)
            if ret != 0:
                return False, checkout_msg
            cmd = 'cd ../branch;python3 releaseVersion.py {} {} {}'.format(self.source_branch, self.target_branch, " ".join(group))
            logger.info("build_package[{}]".format(cmd))
            [ret, release_version_msg] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                return False, release_version_msg
            cmd = 'cd ../branch;python3 changeVersion.py {}'.format(self.target_branch)
            logger.info("build_package[{}]".format(cmd))
            [ret, change_version_msg] = subprocess.getstatusoutput(cmd)
            if ret != 0:
                return False, change_version_msg
            self.commit_and_push(self.target_branch, 'none')
            try:
                if is_build:
                    params = {"branch": self.target_branch, "byCaller": "值班助手"}
                    post_form("http://ops.q7link.com:8000/qqdeploy/projectbuild/", params)
            except Exception as e:
                logger.error(e)
            msg = release_version_msg + change_version_msg
            return True, msg.replace("\n", "").replace("工程", "\n工程")
        except Exception as err:
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    # 切换所有模块的分支
    def checkout_branch(self, branch_name):
        cmd = 'cd ../branch;python3 checkout.py {}'.format(branch_name)
        return subprocess.getstatusoutput(cmd)

    # 重值值班助手环境，切换到master分支，删除本地的target分支
    def rest_branch_env(self):
        self.checkout_branch('master')
        if self.target_branch is not None:
            for project in self.projects.values():
                project.deleteLocalBranch(self.target_branch)
        if self.lock_value is not None:
            self.lock.del_lock("lock", self.lock_value)

    def commit_and_push(self, branch, protect):
        protect_cmd = "cd ../branch;python3 protectBranch.py {} release".format(branch)
        [ret, msg] = subprocess.getstatusoutput(protect_cmd)
        if ret != 0:
            logger.info(msg)
            raise Exception(msg)
        push_cmd = ''
        for name, project in self.projects.items():
            path = project.getPath()
            _, project_branch = subprocess.getstatusoutput('cd {};git branch --show-current'.format(path))
            if project_branch != branch:
                continue
            _, project_commit = subprocess.getstatusoutput("cd {};git status -s".format(path))
            if len(project_commit) < 1:
                continue
            commit_title = "{}-task-0000-修改版本号--{}({})".format(branch, name, self.user_id)
            push_cmd += ';cd ' + path + ';git add .;git commit -m "{}"'.format(commit_title)
            push_cmd += ";git push origin {}".format(branch)
        if len(push_cmd) < 1:
            return
        [ret, msg] = subprocess.getstatusoutput(push_cmd.replace(';', '', 1))
        if ret != 0:
            logger.info(msg)
            raise Exception(msg)
        protect_cmd = "cd ../../branch-manage/branch;python3 protectBranch.py {} {}".format(branch, protect)
        [ret, msg] = subprocess.getstatusoutput(protect_cmd)
        if ret != 0:
            logger.info(msg)
            raise Exception(msg)

if __name__ == "__main__":

    shell = Shell('LuoLin', True, 'stage', 'stage-patch20220910')
    ret, result = shell.create_branch([], ['arap'])
    print(result)



