import time

from wxcrop import Crop
from wxmessage import menu_help, get_pre_map, get_branch_create_map
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
            corp_id, agent_id, permanent_code = self.suite.init_auth_crop()
            Crop(corp_id, self.suite).save_agent_id(agent_id).save_permanent_cod(permanent_code)
        return True

    # 消费数据回调：拉分支、修改版本号、打tag、预制列表方案
    def accept_data(self):
        msg_type = self.data.get('MsgType')
        content = self.data.get('Content')
        user_key = self.data['FromUserName']
        crop = Crop(self.data['ToUserName'], self.suite)
        if msg_type == 'event':
            user_id = crop.get_user_id(user_key)
            help_msg = menu_help.get(self.data.get('EventKey', None), None)
            crop.send_markdown_msg(user_key, help_msg)
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
        user_key = self.data['FromUserName']
        user_id = crop.get_user_id(user_key)
        shell = Shell(user_id, 'init-data')
        try:
            ret, msg = shell.exec_data_pre(data_type, *get_pre_map(params))
            crop.send_text_msg(user_key, str(msg))
        except Exception as err:
            crop.send_text_msg(user_key, str(err))

    # 拉分支
    def create_branch(self, crop, params):
        user_key = self.data['FromUserName']
        user_id = crop.get_user_id()
        shell = Shell(user_id, None)
        try:
            ret, msg = shell.create_branch(*get_branch_create_map(params))
            crop.send_text_msg(user_key, str(ret) + "\n" + str(msg))
        except Exception as err:
            crop.send_text_msg(user_key, "False\n" + str(err))
        pass
