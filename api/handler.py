import time

from wxcrop import Crop
from wxmessage import branch_create, data_pre_old_help, data_pre_new_help, get_pre_map, get_branch_create_map
from shell import Shell
from redislock import RedisLock
from redisclient import redisClient

class Handler:
    def __init__(self, crypt, suite, action, data):
        self.crypt = crypt
        self.suite = suite
        self.action = action
        self.data = data

    def accept(self):
        if self.action == 'command':
            return self.accept_command()
        if self.action == 'data':
            return self.accept_data()

    # 消费指令回调：获取第三方应用凭证；企业接入第三方应用授权
    def accept_command(self):
        info_type = self.data.get('InfoType', '')
        if info_type == 'suite_ticket':
            self.suite.save_ticket(self.data.get('SuiteTicket'))
        if info_type == 'create_auth':
            self.suite.save_auth_code(self.data.get('AuthCode'))
            self.crypt.add_receive(self.suite.init_crop().crop_id)
        return True

    # 消费数据回调：拉分支、修改版本号、打tag、预制列表方案
    def accept_data(self):
        msg_type = self.data.get('MsgType')
        content = self.data.get('Content')
        to_user = self.data['FromUserName']
        crop = Crop(self.data['ToUserName'], self.suite.get_access_token())
        if msg_type == 'event':
            if self.data.get('EventKey', '') == 'data_pre_new':
                crop.send_markdown_msg(to_user, data_pre_new_help)
            if self.data.get('EventKey', '') == 'data_pre_old':
                crop.send_markdown_msg(to_user, data_pre_old_help)
            if self.data.get('EventKey', '') == 'branch_create':
                crop.send_markdown_msg(to_user, branch_create)
        if msg_type == 'text':
            lock = RedisLock(redisClient.get_connection())
            lock_value = lock.get_lock("lock", 120)
            try:
                if '新列表方案' in content:
                    self.exec_data_pre(crop, content.split('\n'), 'new')
                if '老列表方案' in content:
                    self.exec_data_pre(crop, content.split('\n'), 'old')
                if '拉分支' in content:
                    self.create_branch(crop, content.split('\n'))
            finally:
                lock.del_lock("lock", lock_value)


    # 执行脚本预制列表方案
    def exec_data_pre(self, crop, params, data_type):
        user_id = self.data['FromUserName']
        user_name = crop.get_user_name(user_id)
        shell = Shell(user_name, 'init-data')
        try:
            ret, msg = shell.exec_data_pre(data_type, *get_pre_map(params))
            crop.send_text_msg(user_id, str(msg))
        except Exception as err:
            crop.send_text_msg(user_id, str(err))

    # 拉分支
    def create_branch(self, crop, params):
        user_id = self.data['FromUserName']
        user_name = crop.get_user_name()
        shell = Shell(user_name, None)
        try:
            ret, msg = shell.create_branch(*get_branch_create_map(params))
            crop.send_text_msg(user_id, str(ret) + "\n" + str(msg))
        except Exception as err:
            crop.send_text_msg(user_id, "False\n" + str(err))
        pass

