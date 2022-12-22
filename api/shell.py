import re
import time
from log import logger
from concurrent.futures import ThreadPoolExecutor
from redisclient import append, hget, hdel
from redisclient import redisClient
from redislock import RedisLock
from common import Common
executor = ThreadPoolExecutor()


class Shell(Common):
    def __init__(self, user_id, is_test=False, source_branch=None, target_branch=None):
        super().__init__()
        self.user_id = user_id
        self.is_test = is_test
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.lock = RedisLock(redisClient.get_connection())
        self.lock_value = None
        # self.rest_branch_env()

    # 获取目标分支+当前人是否还存在未合并的mr分支
    def get_open_mr_branch(self, mr_key, branch):
        temp_branch = branch + str(int(time.time()))
        mr_ids = hget("q7link-mr-log", mr_key)
        if mr_ids is None:
            return None, temp_branch
        mr_list = self.project_init_data.getProject().mergerequests.list(state='opened', iids=mr_ids.split(","))
        if mr_list is not None and len(mr_list) > 0:
            return mr_list[0], mr_list[0].source_branch
        hdel("q7link-mr-log", mr_key)
        return None, temp_branch

    def create_mr(self, mr_key, opened_mr, temp_branch, branch, title, assignee):
        cmd = 'cd {};git push origin {}'.format(self.project_init_data.getPath(), temp_branch)
        ret, msg = self.exec(cmd, level_info=False)
        if not ret:
            return False, msg
        if opened_mr is not None:
            return True, opened_mr.web_url
        mr = self.project_init_data.createMr(temp_branch, branch, title, assignee)
        append("q7link-mr-log", mr_key, mr.web_url.rsplit("/", 1)[1])
        return True, mr.web_url

    def exec_data_pre(self, data_type, env, tenant_id, target_branch, condition_value, mr_user):
        mr_key = self.user_id + env + tenant_id + self.target_branch
        opened_mr, temp_branch = self.get_open_mr_branch(mr_key, self.target_branch)
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            # 仅当不存在待合并的分支才创建远程分支
            if opened_mr is None:
                self.project_init_data.createBranch(self.target_branch, temp_branch)
            # 删除本地分支
            self.project_init_data.deleteLocalBranch(temp_branch)
            # 在本地将新分支拉取出来
            self.project_init_data.checkout(temp_branch)
            self.chdir_data_pre()
            if data_type == 'new':
                cmd = 'cd ../dataPre;python3 multi.py {} {} {} {} {}'.format(env, tenant_id, temp_branch, self.user_id, condition_value)
                [ret, msg] = self.exec(cmd, level_info=False)
            elif data_type == 'old':
                cmd = 'cd ../dataPre;python3 uiconfig.py {} {} {} {} {}'.format(env, tenant_id, temp_branch, self.user_id, condition_value)
                [ret, msg] = self.exec(cmd, level_info=False)
            else:
                [ret, msg] = False, "unknown cmd"
            self.chdir_branch()
            if not ret:
                raise Exception(msg + "\n预制失败，请检查输出日志")
            mr_title = '<数据预置>前端多列表方案预置-{}'.format(self.user_id)
            return self.create_mr(mr_key, opened_mr, temp_branch, self.target_branch, mr_title, mr_user)
        except Exception as err:
            logger.exception(err)
            self.project_init_data.deleteRemoteBranch(temp_branch)
            return False, str(err)
        finally:
            self.project_init_data.deleteLocalBranch(temp_branch)
            executor.submit(self.rest_branch_env)

    # 获取从来源分支
    def get_slave_source(self):
        if self.is_trunk(self.source_branch):
            return self.source_branch
        branch = self.get_branch_created_source(self.stage_global)
        if branch in self.source_branch:
            return "{}.{}".format(self.stage_global, self.stage)
        return self.stage

    # 创建分支
    def create_branch(self, fixed_version, projects):
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            clear_build_params = self.get_clear_build_params(self.target_branch)
            is_feature_branch = fixed_version != "None"
            if is_feature_branch:
                gen_params = "-v {}".format(fixed_version)
            else:
                gen_params = "-f"
            # self.checkout_branch(self.source_branch)
            slave_source = self.get_slave_source()
            cmd = 'cd ../branch;python3 createBranch.py {}.{} {}.false {}'.format(self.source_branch, slave_source, self.target_branch, " ".join(projects))
            [_, created_msg] = self.exec(cmd, True)
            cmd = 'cd ../branch;python3 genVersion.py {} -s {} -t {} -p {}'.format(gen_params, self.source_branch, self.target_branch, ",".join(projects))
            self.exec(cmd, True, False)
            cmd = 'cd ../branch;python3 changeVersion.py {} {}'.format(self.target_branch, clear_build_params)
            [_, version_msg] = self.exec(cmd, True)
            self.commit_and_push(self.target_branch, 'd' if is_feature_branch else 'hotfix')
            self.ops_build(self.target_branch, self.is_test)
            self.save_branch_created(self.user_id, self.source_branch, self.target_branch, projects)
            created_msg = re.compile('WARNNING：.*\n').sub('', created_msg)
            created_msg = re.compile('工程.*保护成功.*\n').sub('', created_msg)
            return True, (created_msg + "\n" + version_msg)
        except Exception as err:
            logger.exception(err)
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    # 创建前端分支
    def create_front_branch(self, projects):
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            cmd = 'cd ../branch;python3 createBranch.py {}.stage {} {}'.format(self.source_branch, self.target_branch, " ".join(projects))
            [_, created_msg] = self.exec(cmd, True)
            self.save_branch_created(self.user_id, self.source_branch, self.target_branch, projects)
            [_, clear_upgrade] = self.clear_front_upgrade(projects, self.target_branch, "upgrade/release.json")
            [_, protect_msg] = self.protect_branch(self.target_branch, 'hotfix', projects)
            return True, created_msg + clear_upgrade + "\n" + protect_msg
        except Exception as err:
            logger.exception(err)
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env, "front")

    def check_version(self, branch_str):
        try:
            self.lock_value = self.lock.get_lock("lock", 2)
            cmd = 'cd ../branch;python3 checkVersion.py -t compare -b {}'.format(branch_str)
            return self.exec(cmd, level_info=False)
        except Exception as err:
            logger.exception(err)
            return False, str(err)

    def move_branch(self, namespaces):
        try:
            self.lock_value = self.lock.get_lock("lock", 600)
            self.checkout_branch(self.source_branch)
            cmd = 'cd ../branch;python3 backup.py {}.clear {} {},platform,init-data'.format(self.source_branch, self.target_branch, namespaces)
            [_, backup_msg] = self.exec(cmd, True, False)
            backup_msg = re.compile('WARNNING：.*\n').sub('', backup_msg)
            backup_msg = re.compile('工程.*创建分支.*\n').sub('', backup_msg)
            backup_msg = re.compile('工程.*删除分支.*\n').sub('', backup_msg)
            return True, backup_msg
        except Exception as err:
            logger.exception(err)
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    def merge_branch(self, end, projects, clear, user_name):
        try:
            if end == "backend":
                projects = []
            self.lock_value = self.lock.get_lock("lock", 600)
            self.checkout_branch(self.source_branch)
            self.protect_branch(self.target_branch, 'release', projects)
            source = self.source_branch + ".clear" if clear else self.source_branch
            cmd = 'cd ../branch;python3 merge.py {} {} {} {}'.format(end, source, self.target_branch, " ".join(projects))
            [ret, merge_msg] = self.exec(cmd, True)
            if self.is_trunk(self.target_branch):
                access_level = "none"
            else:
                access_level = "hotfix"
            self.protect_branch(self.target_branch, access_level, projects)
            merge_msg = re.compile('WARNNING：.*目标分支.*已存在.*\n').sub('', merge_msg)
            merge_msg = re.compile('工程.*保护成功.*\n').sub('', merge_msg)
            self.send_group_notify(self.source_branch, self.target_branch, projects, ret, user_name)
            return True, merge_msg
        except Exception as err:
            logger.exception(err)
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    def build_package(self, params, protect, is_build):
        try:
            # self.ops_switch_build("stop")
            self.lock_value = self.lock.get_lock("lock", 300)
            self.checkout_branch(self.target_branch)
            cmd = 'cd ../branch;python3 releaseVersion.py {} {} {}'.format(self.source_branch, self.target_branch, params)
            [_, release_version_msg] = self.exec(cmd, True, False)
            cmd = 'cd ../branch;python3 changeVersion.py {}'.format(self.target_branch)
            [_, change_version_msg] = self.exec(cmd, True)
            self.commit_and_push(self.target_branch, protect)
            self.ops_build(self.target_branch, not is_build)
            msg = release_version_msg + change_version_msg
            return True, msg.replace("\n", "").replace("工程", "\n工程")
        except Exception as err:
            logger.exception(err)
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    # 重值值班助手环境，切换到master分支，删除本地的target分支
    def rest_branch_env(self, end="backend"):
        try:
            self.checkout_branch(self.master, end)
            self.delete_branch(self.target_branch, self.projects.values())
            self.delete_branch(self.source_branch, self.projects.values())
            if self.lock_value is not None:
                self.lock.del_lock("lock", self.lock_value)
        except Exception as err:
            logger.exception(err)

    def commit_and_push(self, branch, protect):
        push_cmd = ''
        for name, project in self.projects.items():
            path = project.getPath()
            _, current_branch = self.exec('cd {};git branch --show-current'.format(path), True, False)
            if current_branch != branch:
                continue
            _, project_commit = self.exec("cd {};git status -s".format(path), True, False)
            if len(project_commit) < 1:
                continue
            commit_title = "{}-task-0000-修改版本号--{}({})".format(branch, name, self.user_id)
            push_cmd += ';cd ' + path + ';git add .;git commit -m "{}"'.format(commit_title)
            push_cmd += ";git push origin {}".format(branch)
        if len(push_cmd) < 1:
            return
        self.protect_branch(branch, 'release')
        self.exec(push_cmd.replace(';', '', 1), True, False)
        self.protect_branch(branch, protect)



