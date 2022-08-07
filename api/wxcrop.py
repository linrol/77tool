import time
import json
from log import logger

from wxmessage import msg_params, go_oauth_text_msg
from request import get, post, post_form
from redisclient import redisClient

class Crop:
  def __init__(self, crop_id, suite):
    self.crop_id = crop_id
    self.suite_token = suite.get_access_token()
    self.suite_id = suite.suite_id
    self.suite = suite
    self.crop_key = 'wechat-work-' + self.crop_id

  def get(self, key):
    connection = redisClient.get_connection()
    if not connection.hexists(self.crop_key, key):
      return None
    return redisClient.get_connection().hget(self.crop_key, key)

  def save(self, key, value):
    redisClient.get_connection().hmset(self.crop_key, {key: value})

  def get_permanent_cod(self):
    return self.get('permanent_code')

  def save_permanent_cod(self, value):
    self.save('permanent_code', value)
    return self

  def get_agent_id(self):
    return self.get('agent_id')

  def save_agent_id(self, agent_id):
    self.save('agent_id', agent_id)
    return self

  def get_crop_contact_token(self, crop_id, corp_secret):
    token_expire = self.get('contact_token_expire')
    if token_expire is not None:
      if int(time.time()) - int(token_expire) < 3600:
        return self.get('crop_contact_access_token')

    # 获取企业通讯录的token
    url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}'
    body = get(url.format(crop_id, corp_secret))
    crop_contact_token = body.get('access_token', None)
    if crop_contact_token is None:
      raise Exception(body)
    self.save('crop_contact_access_token', crop_contact_token)
    return crop_contact_token

  def get_corp_token(self):
    token_expire = self.get('token_expire')
    if token_expire is not None:
      if int(time.time()) - int(token_expire) < 3600:
        return self.get('crop_access_token')

    # 第三方应用获取企业token
    url = 'https://qyapi.weixin.qq.com/cgi-bin/service/get_corp_token?suite_access_token={}'
    params = {
      'auth_corpid': self.crop_id,
      'permanent_code': self.get_permanent_cod()
    }
    body = post(url.format(self.suite_token), params)
    crop_access_token = body.get('access_token', None)
    if crop_access_token is None:
      raise Exception(body)
    self.save('crop_access_token', crop_access_token)
    self.save('token_expire', int(time.time()))
    return crop_access_token

  def send_text_msg(self, to_user, content):
    self.send_message(to_user, 'text', {"content": content})

  def send_text_card_msg(self, to_user, content):
    self.send_message(to_user, 'textcard', content)

  def send_markdown_msg(self, to_user, content):
    if content is not None:
      self.send_message(to_user, 'markdown', {"content": content})

  def save_gitlab_auth_info(self, user_auth_code, crop_user_key, user_key):
    params = {
      "client_id": self.suite.gitlab_app_id,
      "client_secret": self.suite.gitlab_secret,
      "code": user_auth_code,
      "grant_type": "authorization_code",
      "redirect_uri": "https://branch.{}/gitlab/oauth?crop_user_key={}".format(self.suite.domain, crop_user_key)
    }
    body = post_form("http://{}/oauth/token".format(self.suite.gitlab_domain), params)
    git_access_token = body.get("access_token")
    git_refresh_token = body.get("refresh_token")
    auth_user = get("http://{}/api/v4/user?access_token={}".format(self.suite.gitlab_domain, git_access_token))
    self.save("{}-q7link-gitlab".format(user_key), json.dumps({"user_id": auth_user.get("username"), "git_refresh_token": git_refresh_token}))
    return "授权成功，请关闭本页面回到企业微信继续操作"

  def get_user_id(self, user_key):
    user_info = self.get("{}-q7link-gitlab".format(user_key))
    if user_info is None:
      redirect_uri = "https://branch.{}/gitlab/oauth?crop_user_key={}".format(self.suite.domain, self.crop_id + ">" + user_key)
      auth_url = "http://{}/oauth/authorize?client_id={}&response_type=code&redirect_uri={}".format(self.suite.gitlab_domain, self.suite.gitlab_app_id, redirect_uri)
      short_body = post("https://durl-openapi.{}/url".format(self.suite.domain), {"fullUrl": auth_url, "expirationTime": 0, "isFrozen": 0})
      short_url = "https://durl.{}/{}".format(self.suite.domain, short_body.get("data").get("shortKey"))
      # go_oauth_msg['url'] = auth_url
      # go_oauth_msg['description'] = go_oauth_msg.get('description').format(short_url)
      self.send_text_msg(user_key, go_oauth_text_msg.format(short_url, short_url))
      raise Exception("需用户授权同意后操作")
    return json.loads(user_info).get("user_id", None)

  def send_message(self, to_user, msg_type, content):
    msg_params['touser'] = to_user
    msg_params["msgtype"] = msg_type
    msg_params["agentid"] = self.get_agent_id()
    msg_params[msg_type] = content
    url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}'
    body = post(url.format(self.get_corp_token()), msg_params)
    logger.info(body)