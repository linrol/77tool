import re
import time
from log import logger
from concurrent.futures import ThreadPoolExecutor
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

    def create_mr(self, temp_branch, branch, title, assignee):
        cmd = 'cd {};git push origin {}'.format(self.project_init_data.getPath(), temp_branch)
        ret, msg = self.exec(cmd, level_info=False)
        if not ret:
            return False, msg
        mr = self.project_init_data.createMr(temp_branch, branch, title, assignee)
        return True, mr.web_url

    def exec_data_pre(self, data_type, env, tenant_id, target_branch, condition_value, mr_user):
        temp_branch = self.target_branch + "_" + str(int(time.time()))
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            # 创建远程分支
            self.project_init_data.createBranch(self.target_branch, temp_branch)
            # 删除本地分支
            self.project_init_data.deleteLocalBranch(temp_branch)
            # 在本地将新分支拉取出来
            self.project_init_data.checkout(temp_branch)
            self.chdir_data_pre()
            user_name = self.userid2name(self.user_id)
            if data_type == 'new':
                cmd = 'cd ../dataPre;python3 multi.py -e {} -t {} -b {} -u {} -c "{}"'.format(env, tenant_id, temp_branch, user_name, condition_value)
                [ret, msg] = self.exec(cmd, level_info=False)
            elif data_type == 'old':
                cmd = 'cd ../dataPre;python3 uiconfig.py {} {} {} {} "{}"'.format(env, tenant_id, temp_branch, user_name, condition_value)
                [ret, msg] = self.exec(cmd, level_info=False)
            else:
                [ret, msg] = False, "unknown cmd"
            self.chdir_branch()
            if not ret:
                raise Exception(msg + "\n预制失败，请检查输出日志")
            mr_title = '<数据预置>前端多列表方案预置-{}'.format(user_name)
            return self.create_mr(temp_branch, self.target_branch, mr_title, mr_user)
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
        end = self.backend
        branch = self.get_branch_created_source(end, self.stage_global)
        if branch is not None and branch in self.source_branch:
            return "{}.{}".format(self.stage_global, self.stage)
        return self.stage

    # 创建分支
    def create_backend_branch(self, fixed_version, projects, req_name):
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            if not self.branch_is_present("build", self.source_branch):
                raise Exception("来源分支【{}】不存在工程【build】".format(self.source_branch))
            clear_build_params = self.get_clear_build_params(self.target_branch)
            is_feature_branch = fixed_version != "None"
            gen_params = "-v {}".format(fixed_version) if is_feature_branch else "-f"
            if not self.branch_is_present('parent', self.target_branch):
                if "platform" in self.get_project_module(projects):
                    projects.append("framework")
            # self.checkout_branch(self.source_branch)
            slave_source = self.get_slave_source()
            cmd = 'cd ../branch;python3 createBranch.py {}.{} {}.false {}'.format(self.source_branch, slave_source, self.target_branch, " ".join(projects))
            [_, created_msg] = self.exec(cmd, True)
            cmd = 'cd ../branch;python3 genVersion.py {} -s {} -t {} -p {}'.format(gen_params, self.source_branch, self.target_branch, ",".join(projects))
            self.exec(cmd, True, True)
            cmd = 'cd ../branch;python3 changeVersion.py {} {}'.format(self.target_branch, clear_build_params)
            [_, version_msg] = self.exec(cmd, True)
            self.commit_and_push(self.target_branch, 'd' if is_feature_branch else 'hotfix', req_name)
            self.ops_build(self.target_branch, self.is_test, user_name=req_name)
            self.save_branch_created(self.user_id, self.source_branch, self.target_branch, projects)
            created_msg = re.compile('WARNNING：.*\n').sub('', created_msg)
            created_msg = re.compile('工程.*保护成功.*\n').sub('', created_msg)
            return True, (created_msg + "\n" + version_msg)
        except Exception as err:
            logger.exception(err)
            self.clear_branch(self.target_branch, " ".join(projects))
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    # 创建非后端工程的分支
    def create_other_branch(self, is_feature, projects):
        try:
            self.lock_value = self.lock.get_lock("lock", 300)
            source = self.source_branch + ".stage"
            target = self.target_branch
            [_, created_msg] = self.create_branch(projects, source, target)
            self.save_branch_created(self.user_id, self.source_branch, target, projects)
            [_, clear_upgrade] = self.clear_front_upgrade(projects, target, "upgrade/release.json")
            [_, protect_msg] = self.protect_branch(self.target_branch, 'd' if is_feature else 'hotfix', projects)
            return True, created_msg + clear_upgrade + protect_msg
        except Exception as err:
            logger.exception(err)
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    def check_version(self, branch):
        try:
            self.lock_value = self.lock.get_lock("lock", 2)
            cmd = 'cd ../branch;python3 checkVersion.py -t duplicate -b {}'.format(branch)
            ret, msg = self.exec(cmd, level_info=False)
            if not ret:
                msg = "分支【{}】的版本号和其他分支存在重复，重复结果如下:\n{}".format(branch, msg)
            logger.info("check version ret[{}] msg[{}]".format(ret, msg))
            # self.send_msg_group_notify(self.check_version_web_hook, ret, msg)
            return ret, msg
        except Exception as err:
            logger.exception(err)
            return False, str(err)

    def move_branch(self, end, projects):
        try:
            self.lock_value = self.lock.get_lock("lock", 600)
            if end == self.backend:
                projects.append("platform")
                projects.append("init-data")
            self.checkout_branch(self.source_branch)
            cmd = 'cd ../branch;python3 backup.py {}.clear {} {}'.format(self.source_branch, self.target_branch, ",".join(projects))
            [_, backup_msg] = self.exec(cmd, True, False)
            backup_msg = re.compile('WARNNING：.*\n').sub('', backup_msg)
            backup_msg = re.compile('工程.*创建分支.*\n').sub('', backup_msg)
            backup_msg = re.compile('工程.*删除分支.*\n').sub('', backup_msg)
            self.protect_branch(self.target_branch, 'none', projects)
            return True, backup_msg
        except Exception as err:
            logger.exception(err)
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    def merge_branch(self, end, projects, cluster_str, clear, user_name, merge_trigger):
        try:
            self.lock_value = self.lock.get_lock("lock", 600)
            merge_trigger(self.user_id, self.source_branch, self.target_branch, projects, cluster_str)
            if end == self.backend:
                projects = [self.backend]
            self.checkout_branch(self.source_branch)
            self.protect_branch(self.target_branch, 'release', projects)
            source = self.source_branch + ".clear" if clear else self.source_branch
            cmd = 'cd ../branch;python3 merge.py {} {} {}'.format(source, self.target_branch, " ".join(projects))
            [ret, merge_msg] = self.exec(cmd, True)
            access_level = "none" if self.is_trunk(self.target_branch) else "hotfix"
            self.protect_branch(self.target_branch, access_level, projects)
            merge_msg = re.compile('WARNNING：.*目标分支.*已存在.*\n').sub('', merge_msg)
            merge_msg = re.compile('工程.*保护成功.*\n').sub('', merge_msg)
            self.send_mr_group_notify(self.source_branch, self.target_branch, projects, ret, user_name, end)
            self.notify_rd(self.target_branch, merge_msg)
            return True, merge_msg
        except Exception as err:
            logger.exception(err)
            return False, str(err)
        finally:
            executor.submit(self.rest_branch_env)

    def package(self, action, params, protect, is_build):
        user_name = None
        try:
            user_name = self.userid2name(self.user_id)
            if action not in ["build", "destroy"]:
                return True, str("")
            self.lock_value = self.lock.get_lock("lock", 300)
            self.checkout_branch(self.target_branch)
            cmd = 'cd ../branch;python3 releaseVersion.py {} {} {}'.format( action, self.target_branch, params)
            [_, release_version_msg] = self.exec(cmd, True)
            cmd = 'cd ../branch;python3 changeVersion.py {}'.format(self.target_branch)
            [_, change_version_msg] = self.exec(cmd, True)
            self.commit_and_push(self.target_branch, protect, user_name)
            return True, (release_version_msg + change_version_msg).replace("\n", "").replace("工程", "\n工程")
        except Exception as err:
            logger.exception(err)
            return True, str(err)
        finally:
            self.ops_build(self.target_branch, not is_build, user_name=user_name)
            executor.submit(self.rest_branch_env)

    # 重值研发助手环境，切换到master分支，删除本地的target分支
    def rest_branch_env(self):
        try:
            self.checkout_branch(self.master, self.backend)
            self.checkout_branch(self.master, self.front)
            self.delete_branch(self.target_branch, self.projects.values())
            self.delete_branch(self.source_branch, self.projects.values())
            if self.lock_value is not None:
                self.lock.del_lock("lock", self.lock_value)
        except Exception as err:
            logger.exception(err)

    def commit_and_push(self, branch, protect, user_name):
        push_cmd = ''
        for name, project in self.projects.items():
            path = project.getPath()
            if path is None:
                continue
            _, current_branch = self.exec('cd {};git branch --show-current'.format(path), True, False)
            if current_branch != branch:
                continue
            _, project_commit = self.exec("cd {};git status -s".format(path), True, False)
            if len(project_commit) < 1:
                continue
            commit_title = "{}-task-0000-修改版本号--{}({})".format(branch, name, user_name)
            push_cmd += ';cd ' + path + ';git add .;git commit -m "{}"'.format(commit_title)
            push_cmd += ";git push origin {}".format(branch)
        if len(push_cmd) < 1:
            return
        self.protect_branch(branch, 'release')
        self.exec(push_cmd.replace(';', '', 1), True, False)
        modules = None if len(protect.split(",")) < 2 else [protect.split(",")[1]]
        self.protect_branch(branch, protect.split(",")[0], modules)



