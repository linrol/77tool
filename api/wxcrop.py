import time
from log import logger

from wxmessage import msg_params
from request import post
from redisclient import client

class Crop:
  def __init__(self, crop_id, suite_token):
    self.crop_id = crop_id
    self.suite_token = suite_token
    self.crop_key = 'wechat-work-' + self.crop_id

  def get(self, key):
    return client.hget(self.crop_key, key)

  def save(self, key, value):
    client.hmset(self.crop_key, {key: value})

  def get_permanent_cod(self):
    return self.get('permanent_code')

  def save_permanent_cod(self, value):
    self.save('permanent_code', value)

  def get_agent_id(self):
    return self.get('agent_id')

  def save_agent_id(self, agent_id):
    self.save('agent_id', agent_id)
    pass

  def get_corp_token(self):
    token_expire = self.get('token_expire')
    if token_expire is not None:
      if int(time.time()) - int(token_expire) < 3600:
        return self.get('crop_access_token')

    url = 'https://qyapi.weixin.qq.com/cgi-bin/service/get_corp_token?suite_access_token={}'
    params = {
      'auth_corpid': self.crop_id,
      'permanent_code': self.get_permanent_cod()
    }
    body = post(url.format(self.suite_token), params)
    crop_access_token = body.get('access_token', None)
    if crop_access_token is not None:
      self.save('crop_access_token', crop_access_token)
      self.save('token_expire', int(time.time()))
      return crop_access_token
    logger.error(body)
    raise Exception(body.get('errmsg'))

  def send_text_msg(self, to_user, content):
    self.send_message(to_user, 'text', content)

  def send_markdown_msg(self, to_user, content):
    self.send_message(to_user, 'markdown', content)

  def send_message(self, to_user, msg_type, content):
    msg_params['touser'] = to_user
    msg_params["msgtype"] = msg_type
    msg_params["agentid"] = self.get_agent_id()
    msg_params[msg_type] = {"content" : content}
    url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}'
    body = post(url.format(self.get_corp_token()), msg_params)
    logger.info(body)