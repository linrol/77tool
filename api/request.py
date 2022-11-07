import requests
import json
from log import logger


def get(url):
    response = requests.get(url)
    body = json.loads(response.text)
    if body.get('errcode', '0') != 0 and 'errmsg' in body:
        logger.error(body.get('errmsg'))
        raise Exception(body.get('errmsg'))
    return body

def post(url, params):
    # s = requests.session()
    # s.proxies = {'https': 'socks5://127.0.0.1:1090'}
    response = requests.post(url, json.dumps(params, ensure_ascii=False).encode('utf-8'))
    body = json.loads(response.text)
    if body.get('errcode', '0') != 0 and 'errmsg' in body:
        logger.error(body.get('errmsg'))
        raise Exception(body.get('errmsg'))
    return body

def post_form(url, params):
    response = requests.post(url, data=params)
    body = json.loads(response.text)
    if response.status_code != 200:
        logger.error(body)
        raise Exception(body)
    return body

