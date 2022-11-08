import time
from request import get, post
from redisclient import redisClient
from wxcrypt import WXBizMsgCrypt
from wxmessage import msg
from log import logger


class Crop:
  def __init__(self, args):
    self.args = args
    self.isdev = args.env != 'prod'
    self.domain = args.domain
    self.gitlab_domain = args.gitlab_domain
    self.gitlab_app_id = args.gitlab_app_id
    self.gitlab_secret = args.gitlab_secret

    self.crop_id = args.crop_id
    self.crop_secret = args.crop_secret
    self.crop_key = 'wechat-work-' + args.crop_id
    self.crypt = self.init_crypt()


  def get(self, key):
    return redisClient.get_connection().hget(self.crop_id, key)

  def save(self, key, value):
    redisClient.get_connection().hmset(self.crop_id, {key: value})

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
    url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}'
    body = get(url.format(self.crop_id, self.crop_secret))
    access_token = body.get('access_token', None)
    self.save('access_token', access_token)
    self.save('token_expire', int(time.time()))
    return access_token

  def create_button(self):
    url = "https://qyapi.weixin.qq.com/cgi-bin/menu/create?access_token={}&agentid={}"
    params = {
      "button":[
        {
          "name":"分支管理",
          "sub_button":[
            {
              "type":"click",
              "name":"拉分支",
              "key":"branch_create"
            },
            {
              "type":"click",
              "name":"分支迁移",
              "key":"branch_move"
            },
            {
              "type":"click",
              "name":"分支合并",
              "key":"branch_merge"
            },
            {
              "type":"click",
              "name":"分支保护",
              "key":"branch_protect"
            },
            {
              "type":"click",
              "name":"构建发布包",
              "key":"build_release_package"
            }
          ]
        },
        {
          "name":"预制数据",
          "sub_button":[
            {
              "type":"click",
              "name":"新列表方案",
              "key":"data_pre_new"
            },
            {
              "type":"click",
              "name":"老列表方案",
              "key":"data_pre_old"
            }
          ]
        }
      ]
    }
    body = post(url.format(self.get_access_token(), self.get_agent_id()), params)
    logger.info(body)

  def send_message(self, to_user, msg_type, content):
    msg['touser'] = to_user
    msg["msgtype"] = msg_type
    msg["agentid"] = self.get_agent_id()
    msg[msg_type] = content
    url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}'
    return post(url.format(self.get_access_token()), msg)
    # logger.info(body)

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

  def get_duty_info(self, is_test, fixed_user_ids, end="backend"):
    if self.isdev or is_test:
      return "LuoLin", "罗林"
    else:
      body = get("http://10.0.144.51:5000/api/verify/duty/users")
      role_duty_info = body.get("data").get(end)
      duty_user_ids = []
      duty_user_names = []
      for duty in role_duty_info:
        duty_user_ids.append(duty.get("user_id"))
        duty_user_names.append(duty.get("user_name"))
      if len(fixed_user_ids) > 0:
        duty_user_ids.extend(fixed_user_ids)
      return "|".join(duty_user_ids), ",".join(duty_user_names)

  def user_id2name(self, user_id):
    user_name = self.get("{}-userinfo".format(user_id))
    if user_name is not None:
      return user_name
    url = "https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={}&userid={}"
    body = get(url.format(self.get_access_token(), user_id))
    self.save("{}-userinfo".format(user_id), body.get("name"))
    return body.get("name")

  def user_name2id(self, user_name):
    try:
      if user_name is None:
        return None
      body = get("http://10.0.144.51:5000/api/verify/duty/user_id?user_name={}".format(user_name))
      return body.get("data")[0].get("user_id")
    except Exception as err:
      print(str(err))
      return None


  def disable_task_button(self, task_code, button_text):
    params = {
      # "userids": [user_id],
      "atall": 1,
      "agentid": self.get_agent_id(),
      "response_code": task_code,
      "button": {
        "replace_name": button_text
      }
    }
    url = "https://qyapi.weixin.qq.com/cgi-bin/message/update_template_card?access_token={}"
    return post(url.format(self.get_access_token()), params)

