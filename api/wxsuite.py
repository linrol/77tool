import time
from log import logger
from request import post
from redisclient import redisClient

class Suite:
  def __init__(self, domain, gitlab_domain, gitlab_app_id, gitlab_secret, suite_id, suite_secret):
    self.domain = domain
    self.gitlab_domain = gitlab_domain
    self.gitlab_app_id = gitlab_app_id
    self.gitlab_secret = gitlab_secret

    self.suite_id = suite_id
    self.suite_secret = suite_secret
    self.suite_key = 'wechat-work-' + suite_id

  def get(self, key):
    return redisClient.get_connection().hget(self.suite_key, key)

  def save(self, key, value):
    redisClient.get_connection().hmset(self.suite_key, {key: value})

  def get_ticket(self):
    return self.get('suite_ticket')

  def save_ticket(self, value):
    self.save('suite_ticket', value)
    self.get_access_token()

  def get_auth_code(self):
    return self.get('auth_code')

  def save_auth_code(self, value):
    self.save('auth_code', value)

  def get_access_token(self):
    token_expire = self.get('token_expire')
    if token_expire is not None:
      if int(time.time()) - int(token_expire) < 3600:
        return self.get('suite_access_token')
    suite_ticket = self.get('suite_ticket')
    url = 'https://qyapi.weixin.qq.com/cgi-bin/service/get_suite_token'
    params = {
      'suite_id': self.suite_id,
      'suite_secret': self.suite_secret,
      'suite_ticket': suite_ticket
    }
    body = post(url, params)
    suite_access_token = body.get('suite_access_token', None)
    if suite_access_token is not None:
      self.save('suite_access_token', suite_access_token)
      self.save('token_expire', int(time.time()))
      return suite_access_token
    logger.error(body)
    raise Exception(body)

  def init_auth_crop(self):
    suite_token = self.get_access_token()
    url = 'https://qyapi.weixin.qq.com/cgi-bin/service/get_permanent_code?suite_access_token={}'
    params = {'auth_code': self.get_auth_code()}
    body = post(url.format(suite_token), params)
    corp_id = body.get('auth_corp_info').get('corpid')
    agent_id = body.get('auth_info').get('agent')[0].get('agentid')
    permanent_code = body.get('permanent_code')
    self.add_auth_corp_ids(corp_id)
    return corp_id, agent_id, permanent_code

  def get_auth_crop_ids(self):
    return self.get('auth_corp_ids')

  def add_auth_corp_ids(self, corp_id):
    auth_corp_ids = self.get('auth_corp_ids')
    if auth_corp_ids is not None and corp_id in auth_corp_ids:
      return
    auth_corp_ids = corp_id if auth_corp_ids is None else corp_id + ',' + auth_corp_ids
    self.save('auth_corp_ids', auth_corp_ids)