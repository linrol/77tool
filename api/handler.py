import os
from wxcrop import Crop
from wxmessage import data_pre_old_help, data_pre_new_help, get_pre_map
from shell import Shell

class Handler:
    def __init__(self, crypt, suite, action, data):
        self.crypt = crypt
        self.suite = suite
        self.action = action
        self.data = data

    async def accept(self):
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
        return "success"

    # 消费数据回调：拉分支、修改版本号、打tag、预制列表方案
    def accept_data(self):
        msg_type = self.data.get('MsgType')
        content = self.data.get('Content')
        to_user = self.data['FromUserName']
        crop = Crop(self.data['ToUserName'], self.suite.get_access_token())
        if msg_type == 'event' and self.data.get('EventKey', '') == 'new':
            crop.send_markdown_msg(to_user, data_pre_new_help)
        if msg_type == 'event' and self.data.get('EventKey', '') == 'old':
            crop.send_markdown_msg(to_user, data_pre_old_help)
        if msg_type == 'text' and '新列表方案' in content:
            self.exec_data_pre(crop, content.split('\n'), 'new')
        if msg_type == 'text' and '老列表方案' in content:
            self.exec_data_pre(crop, content.split('\n'), 'old')

    # 执行脚本预制新列表方案
    def exec_data_pre(self, crop, params, data_type):
        shell = Shell('init-data')
        from_user = self.data['FromUserName']
        try:
            ret, msg = shell.exec_data_pre(from_user, data_type, *get_pre_map(params))
            crop.send_text_msg(from_user, str(msg))
        except Exception as err:
            crop.send_text_msg(from_user, str(err))
