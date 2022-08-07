from wxcrop import Crop
from wxmessage import menu_help, get_pre_map, get_branch_create_map
from shell import Shell
from redislock import RedisLock
from redisclient import redisClient, duplicate_msg
from log import logger

class Handler:
    def __init__(self, crypt, suite, action, data):
        self.crypt = crypt
        self.suite = suite
        self.action = action
        self.data = data

    def accept(self):
        if duplicate_msg(self.data):
            return "duplicate accept"
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
            help_msg = menu_help.get(self.data.get('EventKey', None), None)
            if help_msg is not None and crop.get_user_id(user_key):
                crop.send_markdown_msg(user_key, help_msg)
        if msg_type == 'text':
            if not ('新列表方案' in content or '老列表方案' in content or'拉分支' in content):
                logger.info("ignore message:{}", self.data)
                return "ignore message"
            ret_msg = None
            user_id = None
            try:
                lock = RedisLock(redisClient.get_connection())
                lock_value = lock.get_lock("lock", 300)
                user_id = crop.get_user_id(user_key)
                if '新列表方案' in content:
                    ret, ret_msg = self.exec_data_pre(user_id, content.split('\n'), 'new', lock, lock_value)
                if '老列表方案' in content:
                    ret, ret_msg = self.exec_data_pre(user_id, content.split('\n'), 'old', lock, lock_value)
                if '拉分支' in content:
                    ret, ret_msg = self.create_branch(user_id, content.split('\n'), lock, lock_value)
            except Exception as err:
                ret_msg = str(err)
            finally:
                # lock.del_lock("lock", lock_value)
                crop.send_text_msg(user_key, str(ret_msg))
                logger.info("* {}_{} ret: {}".format(user_id, self.data.get('MsgId', ''), str(ret_msg)))



    # 执行脚本预制列表方案
    def exec_data_pre(self, user_id, params, data_type, lock, lock_value):
        pre_map = get_pre_map(params)
        shell = Shell(user_id, lock, lock_value, target_branch=pre_map[3])
        return shell.exec_data_pre(data_type, *pre_map)

    # 拉分支
    def create_branch(self, user_id, params, lock, lock_value):
        source, target, project_names = get_branch_create_map(params)
        shell = Shell(user_id, lock, lock_value, source, target)
        return shell.create_branch(project_names)
