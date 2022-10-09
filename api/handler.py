import random
import string

from shell import Shell
from task import Task
from log import logger
from wxmessage import menu_help, get_pre_dirt, get_branch_dirt, get_init_feature_dirt, get_build_dirt, get_merge_branch_dirt, get_move_branch_dirt, xml2dirt
from redisclient import duplicate_msg, get_create_branch_task, hmset

require_git_oauth_event = ["data_pre_new", "data_pre_old"]


class Handler:
    def __init__(self, crypt, crop, raw_content):
        self.crypt = crypt
        self.crop = crop
        self.data = xml2dirt(raw_content)
        # 消息内容
        self.msg_id = self.data.get('MsgId', '')
        self.msg_content = self.data.get('Content', '')
        self.is_test = 'isTest=true' in self.msg_content
        # 可能时密文或者明文
        self.user_id = self.data['FromUserName']
        self.user_name = self.crop.user_id2name(self.user_id)
        # 消息类型
        self.msg_type = self.data.get('MsgType', '')
        self.is_text_msg = self.msg_type == 'text'
        self.event_key = self.data.get('EventKey', '')
        self.event_task_id = self.data.get('TaskId', None)
        self.event_task_code = self.data.get('ResponseCode', None)
        self.is_event_task = self.event_task_id is not None
        self.is_event_msg = self.msg_type == 'event' and not self.is_event_task

    def accept(self):
        if duplicate_msg(self.data):
            accept_ret = "duplicate accept"
        elif self.is_event_msg:
            accept_ret = self.accept_event()
        elif self.is_event_task:
            accept_ret = self.accept_event_task()
        else:
            accept_ret = self.accept_data()
        logger.info("* {}_{} accept ret: {}".format(self.user_name, self.msg_id,
                                                    accept_ret))
        return accept_ret

    # 消费事件消息
    def accept_event(self):
        help_msg = menu_help.get(self.event_key, None)
        if help_msg is None:
            return "event key {} are not listening".format(self.event_key)
        # if not self.require_git_auth():
        #     return "need to gitlab authorization"
        self.crop.send_markdown_msg(self.user_id, help_msg)
        return help_msg

    # 消费事件任务类消息
    def accept_event_task(self):
        task_content = get_create_branch_task(self.event_task_id)
        if task_content is None:
            return "event task {} not found".format(self.event_task_id)
        task_contents = task_content.split("#")
        req_user_id = task_contents[0]
        task_code = task_contents[1]
        projects = task_contents[2]
        _operation = self.event_key.split("@")[0]
        if _operation == 'deny':
            # 拒绝任务
            self.crop.disable_task_button(self.event_task_code, "已拒绝")
            return "deny task[{}]".format(task_content)
        # 同意任务
        self.crop.disable_task_button(self.event_task_code, "任务执行中...")
        project_list = projects.split(",")
        self.is_test = task_contents[3] == "True"
        fixed_version = None
        if len(task_contents) > 4:
            fixed_version = task_contents[4]
        task_info = self.event_task_id.split("@")
        ret_msg = self.create_branch(req_user_id, task_info[1], task_info[2],
                                     project_list, fixed_version)
        self.crop.disable_task_button(task_code, "任务执行完成")
        return ret_msg

    # 验证是否为监听的内容
    def is_listen_content(self):
        return '新列表方案' in self.msg_content or \
               '老列表方案' in self.msg_content or \
               '拉分支' in self.msg_content or \
               '分支迁移' in self.msg_content or \
               '分支合并' in self.msg_content or \
               '构建发布包' in self.msg_content or \
               '初始化特性分支' in self.msg_content

    # 消费数据回调：拉分支、修改版本号、打tag、预制列表方案
    def accept_data(self):
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
            return self.move_branch()
        elif '分支合并' in self.msg_content:
            return self.merge_branch()
        elif '构建发布包' in self.msg_content:
            return self.build_package()
        elif '初始化特性分支' in self.msg_content:
            return self.init_feature_branch()

    # 执行脚本预制列表方案
    def data_pre(self, pre_type):
        try:
            data_pre_dirt = get_pre_dirt(self.msg_content)
            shell = Shell(self.user_id, target_branch=data_pre_dirt[2])
            ret, result = shell.exec_data_pre(pre_type, *data_pre_dirt)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(result))
            if data_pre_dirt[3] is not None:
                merge_user_id = self.crop.user_name2id(data_pre_dirt[3])
                self.crop.send_text_msg(merge_user_id, str(result))
            return result
        except Exception as err:
            print(str(err))
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    # 拉分支
    def create_branch(self, apply_user_id, source, target, projects,
        fixed_version):
        shell = Shell(apply_user_id, self.is_test, source, target)
        ret, result = shell.create_branch(fixed_version, projects)
        # 发送消息通知
        notify_user_ids = "|".join({self.user_id, apply_user_id})
        self.crop.send_text_msg(notify_user_ids, str(result))
        return result

    def move_branch(self):
        try:
            duty_user_id, name = self.crop.get_duty_info(self.is_test, ["LuoLin"])
            if self.user_id not in duty_user_id:
                raise Exception("仅限当周后端值班人：{}操作".format(name))
            source, target, namespaces = get_move_branch_dirt(self.msg_content)
            if "sprint" not in source:
                raise Exception("迁移分支输入错误，当前仅支持班车sprint分支")
            shell = Shell(self.user_id, self.is_test, source, target)
            ret, result = shell.move_branch(namespaces)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(result))
            return result
        except Exception as err:
            print(str(err))
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    def merge_branch(self):
        try:
            duty_user_id, name = self.crop.get_duty_info(self.is_test, ["LuoLin"])
            if self.user_id not in duty_user_id:
                raise Exception("仅限当周后端值班人：{}操作".format(name))
            source, target, clear_source = get_merge_branch_dirt(self.msg_content)
            shell = Shell(self.user_id, self.is_test, source, target)
            ret, result = shell.merge_branch(clear_source)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(result))
            return result
        except Exception as err:
            print(str(err))
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    def build_package(self):
        try:
            duty_user_id, name = self.crop.get_duty_info(self.is_test, ["LuoLin"])
            if self.user_id not in duty_user_id:
                raise Exception("仅限当周后端值班人：{}操作".format(name))
            target, params, protect, is_build = get_build_dirt(self.msg_content)
            shell = Shell(self.user_id, self.is_test, 'master', target)
            ret, result = shell.build_package(params, protect, is_build)
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(result))
            return result
        except Exception as err:
            print(str(err))
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    # 创建拉分支的任务
    def new_branch_task(self):
        try:
            req_user = (self.user_id, self.user_name)
            fixed_ids = ["LuoLin", "XieXiaNiDeGuanYu",
                              "yunpeng.liu@q7link.com"]
            duty_user = self.crop.get_duty_info(self.is_test, fixed_ids)
            task_info = req_user + duty_user + get_branch_dirt(self.msg_content)
            ret = Task(self.is_test).new_branch_task(self.crop, *task_info)
            self.crop.send_text_msg(self.user_id, ret)
            return "create project[{}] branch[{}] task success".format(
                task_info[-1], task_info[-2])
        except Exception as err:
            print(str(err))
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

    def init_feature_branch(self):
        try:
            init_feature = get_init_feature_dirt(self.msg_content)
            target = init_feature.get("目标分支")
            source = init_feature.get("来源分支")
            prefix = Task().get_branch_version(source).get("framework")
            last_version = ''.join(random.sample(string.ascii_letters, 6))
            version = "{}.{}-SNAPSHOT".format(prefix.replace("-SNAPSHOT", ""),
                                              last_version)
            approve_user = init_feature.get("分支负责人")
            value = "{}@{}@{}".format(source, version, approve_user)
            hmset("q7link-branch-feature", {target: value})
            self.crop.send_text_msg(self.user_id, "分支初始化成功，请重新发起拉分支请求")
        except Exception as err:
            print(str(err))
            # 发送消息通知
            self.crop.send_text_msg(self.user_id, str(err))
            return str(err)

