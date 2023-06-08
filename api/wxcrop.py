import time
from request import get, post
from redisclient import hget, hmset
from wxcrypt import WXBizMsgCrypt
from wxmessage import msg
from log import logger


class Crop:
    def __init__(self, args):
        self.args = args
        self.crop_id = args.crop_id
        self.crop_secret = args.crop_secret
        self.crypt = self.init_crypt()
        self.work_wx_url = "https://qyapi.weixin.qq.com"

    def get(self, key):
        return hget(self.crop_id, key)

    def save(self, key, value):
        hmset(self.crop_id, {key: value})

    def get_agent_id(self):
        return self.get("agent_id")

    def init_crypt(self):
        return WXBizMsgCrypt(self.args.token, self.args.aes_key, {self.crop_id})

    def get_crypt(self):
        if self.crypt is None:
            self.init_crypt()
        return self.crypt

    def get_access_token(self):
        token_expire = self.get('token_expire')
        if token_expire is not None:
            if int(time.time()) - int(token_expire) < 3600:
                return self.get('access_token')
        url = '{}/cgi-bin/gettoken?corpid={}&corpsecret={}'
        body = get(url.format(self.work_wx_url, self.crop_id, self.crop_secret))
        access_token = body.get('access_token', None)
        self.save('access_token', access_token)
        self.save('token_expire', int(time.time()))
        return access_token

    def create_button(self):
        url = "{}/cgi-bin/menu/create?access_token={}&agentid={}"
        params = {
            "button": [
                {
                    "name": "分支管理",
                    "sub_button": [
                        {
                            "type": "click",
                            "name": "拉分支",
                            "key": "branch_create"
                        },
                        {
                            "type": "click",
                            "name": "分支迁移",
                            "key": "branch_move"
                        },
                        {
                            "type": "click",
                            "name": "分支合并",
                            "key": "branch_merge"
                        },
                        {
                            "type": "click",
                            "name": "分支保护",
                            "key": "branch_protect"
                        },
                        {
                            "type": "click",
                            "name": "构建发布包",
                            "key": "build_release_package"
                        }
                    ]
                },
                {
                    "name": "预制数据",
                    "sub_button": [
                        {
                            "type": "click",
                            "name": "新列表方案",
                            "key": "data_pre_new"
                        },
                        {
                            "type": "click",
                            "name": "老列表方案",
                            "key": "data_pre_old"
                        }
                    ]
                }
            ]
        }
        body = post(url.format(self.work_wx_url, self.get_access_token(),
                               self.get_agent_id()), params)
        logger.info(body)

    def send_message(self, to_user, msg_type, content):
        msg['touser'] = to_user
        msg["msgtype"] = msg_type
        msg["agentid"] = self.get_agent_id()
        msg[msg_type] = content
        url = '{}/cgi-bin/message/send?access_token={}'
        return post(url.format(self.work_wx_url, self.get_access_token()), msg)

    def send_template_card(self, to_user, content):
        return self.send_message(to_user, 'template_card', content)

    def send_text_msg(self, to_user, content):
        if content is None:
            return None
        return self.send_message(to_user, 'text', {"content": content})

    def send_text_card_msg(self, to_user, content):
        return self.send_message(to_user, 'textcard', content)

    def send_markdown_msg(self, to_user, content):
        return self.send_message(to_user, 'markdown', {"content": content})

    def userid2name(self, user_id):
        user_name = self.get("{}-userinfo".format(user_id))
        if user_name is not None:
            return user_name
        url = "{}/cgi-bin/user/get?access_token={}&userid={}"
        body = get(url.format(self.work_wx_url, self.get_access_token(),
                              user_id))
        self.save("{}-userinfo".format(user_id), body.get("name"))
        return body.get("name")

    def disable_task_button(self, task_code, button_text):
        params = {
            "atall": 1,
            "agentid": self.get_agent_id(),
            "response_code": task_code,
            "button": {
                "replace_name": button_text
            }
        }
        url = "{}/cgi-bin/message/update_template_card?access_token={}"
        return post(url.format(self.work_wx_url, self.get_access_token()),
                    params)
