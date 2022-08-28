import time
import json
from request import get, post, post_form
from redisclient import redisClient
from wxcrypt import WXBizMsgCrypt
from wxmessage import msg, msg_content
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
    return self.send_message(to_user, 'text', {"content": content})

  def send_text_card_msg(self, to_user, content):
    return self.send_message(to_user, 'textcard', content)

  def send_markdown_msg(self, to_user, content):
    return self.send_message(to_user, 'markdown', {"content": content})


  def get_duty_info(self, role, is_test):
    if self.isdev or is_test:
      return "LuoLin", "罗林"
    else:
      body = get("http://10.0.144.51:5000/api/verify/duty/users")
      role_duty_info = body.get("data").get(role)
      duty_user_ids = []
      duty_user_names = []
      for duty in role_duty_info:
        duty_user_ids.append(duty.get("user_id"))
        duty_user_names.append(duty.get("user_name"))
      return "|".join(duty_user_ids), ",".join(duty_user_names)

  def get_gitlab_user_id(self, user_key):
    user_info = self.get("{}-q7link-gitlab".format(user_key))
    if user_info is None:
      redirect_uri = "https://branch.{}/gitlab/oauth?user_key={}".format(self.domain, user_key)
      auth_url = "http://{}/oauth/authorize?client_id={}&response_type=code&redirect_uri={}".format(self.gitlab_domain, self.gitlab_app_id, redirect_uri)
      short_body = post("https://durl-openapi.{}/url".format(self.domain), {"fullUrl": auth_url, "expirationTime": 0, "isFrozen": 0})
      short_url = "https://durl.{}/{}".format(self.domain, short_body.get("data").get("shortKey"))
      self.send_text_msg(user_key, msg_content.get("oauth_text_msg").format(short_url, short_url))
      raise Exception("需用户授权同意后操作")
    return json.loads(user_info).get("user_id", None)

  def get_user_name(self, user_id):
    user_name = self.get("{}-userinfo".format(user_id))
    if user_name is not None:
      return user_name
    url = "https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={}&userid={}"
    body = get(url.format(self.get_access_token(), user_id))
    self.save("{}-userinfo".format(user_id), body.get("name"))
    return body.get("name")


  def save_gitlab_auth_info(self, user_auth_code, user_key):
    params = {
      "client_id": self.gitlab_app_id,
      "client_secret": self.gitlab_secret,
      "code": user_auth_code,
      "grant_type": "authorization_code",
      "redirect_uri": "https://branch.{}/gitlab/oauth?crop_user_key={}".format(self.domain, user_key)
    }
    body = post_form("http://{}/oauth/token".format(self.gitlab_domain), params)
    git_access_token = body.get("access_token")
    git_refresh_token = body.get("refresh_token")
    auth_user = get("http://{}/api/v4/user?access_token={}".format(self.gitlab_domain, git_access_token))
    self.save("{}-q7link-gitlab".format(user_key), json.dumps({"user_id": auth_user.get("username"), "git_refresh_token": git_refresh_token}))
    return "授权成功，请关闭本页面回到企业微信继续操作"

  def disable_task_button(self, user_id, task_code, button_text):
    params = {
      "userids": [user_id],
      "agentid": self.get_agent_id(),
      "response_code": task_code,
      "button": {
        "replace_name": button_text
      }
    }
    url = "https://qyapi.weixin.qq.com/cgi-bin/message/update_template_card?access_token={}"
    return post(url.format(self.get_access_token()), params)

