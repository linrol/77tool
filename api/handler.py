from shell import Shell
from task import Task
from log import logger
from base import Base
from wxmessage import menu_help, get_pre_dirt, get_branch_dirt, get_init_feature_dirt, get_build_dirt, get_merge_branch_dirt, get_protect_branch_dirt, get_move_branch_dirt
from redisclient import duplicate_msg, get_user_task, no_task_depend


class Handler(Base):
    def __init__(self, crop, data):
        self.crop = crop
        self.data = data
        # 消息内容
        self.msg_id = self.data.get('MsgId', '')
        self.msg_content = self.data.get('Content', '')
        self.is_test = 'isTest=true' in self.msg_content
        # 可能时密文或者明文
        self.user_id = self.data['FromUserName']
        self.user_name = self.crop.userid2name(self.user_id)
        # 消息类型
        self.msg_type = self.data.get('MsgType', '')
        self.is_text_msg = self.msg_type == 'text'
        self.event_key = self.data.get('EventKey', '')
        self.event_task_id = self.data.get('TaskId', None)
        self.event_task_code = self.data.get('ResponseCode', None)
        self.is_event_task = self.event_task_id is not None
        self.is_event_msg = self.msg_type == 'event' and not self.is_event_task

    def accept(self):
        logger.info("* {} accept request: {}".format(self.user_name, self.data))
        try:
            if duplicate_msg(self.data):
                ret = "duplicate accept"
            elif self.is_event_msg:
                ret = self.accept_event()
            elif self.is_event_task:
                ret = self.accept_event_task()
            else:
                ret = self.accept_message()
            logger.info("* {} accept response: {}".format(self.user_name, ret))
            return ret
        except Exception as err:
            logger.info("* {} accept response: {}".format(self.user_name, str(err)))
            return str(err)

    # 消费事件消息
    def accept_event(self):
        help_msg = menu_help.get(self.event_key, None)
        if help_msg is None:
            return "event key {} are not listening".format(self.event_key)
        self.crop.send_markdown_msg(self.user_id, help_msg)
        return help_msg

    # 消费事件任务类消息
    def accept_event_task(self):
        read_ids = self.get_readonly_duties()
        if self.user_id is not None and self.user_id in read_ids:
            msg = "您无权限操作！"
            self.crop.send_text_msg(self.user_id, msg)
            return msg
        action = self.event_key.split("@")[0]
        action_type = self.event_key.split("@")[1]
        if action == 'deny':
            # 拒绝任务
            self.crop.disable_task_button(self.event_task_code, "已拒绝")
            return "deny task[{}]".format(self.event_task_id)
        # 同意任务
        self.crop.disable_task_button(self.event_task_code, "任务执行中...")
        task_content = get_user_task(self.event_task_id)
        if task_content is None:
            return "agree task {} not found".format(self.event_task_id)
        task_contents = task_content.split("#")
        self.is_test = task_contents[0] == "True"
        task_code = task_contents[1]
        if action_type == "branch_new":
            ret_msg = self.new_branch(task_contents)
        elif action_type == "branch_merge":
            ret_msg = self.merge_branch(task_contents)
        elif action_type == "branch_move":
            ret_msg = self.move_branch(task_contents)
        else:
            ret_msg = "未知任务"
        self.crop.disable_task_button(task_code, "任务执行完成")
        return ret_msg

    # 验证是否为监听的内容
    def is_listen_content(self):
        return '新列表方案' in self.msg_content or \
               '老列表方案' in self.msg_content or \
               '拉分支' in self.msg_content or \
               '分支迁移' in self.msg_content or \
               '分支合并' in self.msg_content or \
               '分支保护' in self.msg_content or \
               '构建发布包' in self.msg_content or \
               '初始化特性分支' in self.msg_content

    # 消费数据回调：拉分支、修改版本号、打tag、预制列表方案
    def accept_message(self):
        if not self.is_text_msg:
            return "the msg_type [{}] not listening".format(self.msg_type)
        elif not self.is_listen_content():
            return "the msg_content [{}] not listening".format(self.msg_content)
        elif '列表方案' in self.msg_content:
            pre_type = "new" if "新" in self.msg_content else "old"
            return self.data_pre(pre_type)
        elif '拉分支' in self.msg_content:
            return self.new_branch_task()
        elif '分支迁移' in self.msg_content:
            return self.move_branch(None)
        elif '分支合并' in self.msg_content:
            return self.merge_branch(None)
        elif '分支保护' in self.msg_content:
            return self.protect_branch_project(None)
        elif '构建发布包' in self.msg_content:
            return self.build_package()
        elif '初始化特性分支' in self.msg_content:
            return self.init_feature_branch()

    # 执行脚本预制列表方案
    def data_pre(self, pre_type):
        try:
            data_pre_dirt = get_pre_dirt(self.msg_content)
            shell = Shell(self.user_id, target_branch=data_pre_dirt[2])
            self.crop.send_text_msg(self.user_id, "列表方案预制任务运行中，请稍等!")
            ret, result = shell.exec_data_pre(pre_type, *data_pre_dirt)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(result))
            result = "收到来自{}预制数据代码合并请求，请合并\n{}".format(self.user_name,
                                                                  str(result))
            assignee_userid = self.name2userid(data_pre_dirt[4])
            if assignee_userid is not None and assignee_userid != self.user_id:
                self.crop.send_text_msg(assignee_userid, result)
            return result
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    # 拉分支
    def new_branch(self, task_contents):
        try:
            req_id = task_contents[2]
            source = task_contents[3]
            target = task_contents[4]
            projects = task_contents[5].split(",")
            fixed_version = task_contents[6]
            req_name = self.crop.userid2name(req_id)
            shell = Shell(req_id, self.is_test, source, target)
            end = self.get_project_end(projects)
            if end == self.backend:
                _, ret = shell.create_branch(fixed_version, projects, req_name)
            else:
                is_feature = fixed_version != "None"
                _, ret = shell.create_other_branch(is_feature, projects)
            # 发送消息通知
            user_ids = "|".join({self.user_id, req_id})
            self.crop.send_text_msg(user_ids, str(ret))
            return ret
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    def move_branch(self, task_contents):
        try:
            duty_user_id, name = self.get_duty_info(self.is_test)
            if task_contents is None and self.user_id not in duty_user_id:
                raise Exception("仅限当周后端值班人：{}操作".format(name))
            if task_contents is None:
                source, target, namespaces = get_move_branch_dirt(self.msg_content)
            else:
                source = task_contents[2]
                target = task_contents[3]
                namespaces = task_contents[4]
            if "sprint" not in source and "release" not in source:
                raise Exception("迁移分支输入错误，仅支持来源为sprint/release分支")
            self.crop.send_text_msg(self.user_id, "分支迁移任务运行中，请稍等!")
            shell = Shell(self.user_id, self.is_test, source, target)
            _, ret = shell.move_branch(namespaces)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(ret))
            return ret
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    def merge_branch(self, task_contents):
        try:
            if task_contents is None:
                f_duty_id, f_name = self.get_duty_info(self.is_test, self.front)
                b_duty_id, b_name = self.get_duty_info(self.is_test, self.backend)
                if self.user_id not in f_duty_id + b_duty_id:
                    raise Exception("仅限当周值班人：{},{}操作".format(f_name, b_name))
                end = self.backend if self.user_id in b_duty_id else "front"
                source, target, projects, clear = get_merge_branch_dirt(self.msg_content)
                self.crop.send_text_msg(self.user_id, "分支合并任务运行中，请稍等!")
            else:
                source = task_contents[2]
                target = task_contents[3]
                projects = task_contents[4].split(",")
                end = self.get_project_end(projects)
                clear = "true" in self.data.get("SelectedItems").get("SelectedItem").get("OptionIds").get("OptionId") and no_task_depend(self.event_task_id)
            shell = Shell(self.user_id, self.is_test, source, target)
            _, ret = shell.merge_branch(end, projects, clear, self.user_name)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(ret))
            return ret
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    def protect_branch_project(self, task_contents):
        try:
            if task_contents is None:
                target, projects, is_protect = get_protect_branch_dirt(self.msg_content)
                end = self.get_project_end(projects)
                duty_ids, name = self.get_duty_info(self.is_test, end)
                if task_contents is None and self.user_id not in duty_ids:
                    raise Exception("仅限当周值班人：{}操作".format(name))
                self.crop.send_text_msg(self.user_id, "分支保护任务运行中，请稍等!")
            else:
                target = task_contents[1]
                projects = task_contents[2]
                is_protect = "true" in self.data.get("SelectedItems").get("SelectedItem").get("OptionIds").get("OptionId")
            if is_protect:
                protect = "none"
            else:
                protect = "hotfix"
            shell = Shell(self.user_id, self.is_test, self.master, target)
            _, ret = shell.protect_branch(target, protect, projects)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(ret))
            return ret
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    def build_package(self):
        try:
            duty_user_id, name = self.get_duty_info(self.is_test)
            if self.user_id not in duty_user_id:
                raise Exception("仅限当周后端值班人：{}操作".format(name))
            target, params, protect, is_build = get_build_dirt(self.msg_content)
            self.crop.send_text_msg(self.user_id, "构建发布包任务运行中，请稍等!")
            shell = Shell(self.user_id, self.is_test, self.master, target)
            _, ret = shell.build_package(params, protect, is_build)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(ret))
            return ret
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    # 创建拉分支的任务
    def new_branch_task(self):
        try:
            branch_params = get_branch_dirt(self.msg_content)
            end = self.get_project_end(branch_params[2])
            applicant = (self.user_id, self.user_name)
            watchman = self.get_duty_info(self.is_test, end)
            _, ret = Task(self.is_test).new_branch_task(self.crop, end,
                                                        *branch_params,
                                                        applicant=applicant,
                                                        watchman=watchman)
            return ret
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    def init_feature_branch(self):
        try:
            init_feature = get_init_feature_dirt(self.msg_content)
            source = init_feature.get("来源分支")
            target = init_feature.get("目标分支")
            version = Task().gen_feature_version(source)
            feature_version = init_feature.get("分支版本号", version)
            approve_user = init_feature.get("分支负责人")
            self.save_branch_feature(target, source, feature_version,
                                     approve_user)
            self.crop.send_text_msg(self.user_id, "分支初始化成功，请重新发起拉分支请求")
            return "init branch[{}] success".format(target)
        except Exception as err:
            logger.exception(err)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

