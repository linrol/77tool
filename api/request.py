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
    response = requests.post(url, json.dumps(params))
    body = json.loads(response.text)
    if body.get('errcode', '0') != 0 and 'errmsg' in body:
        logger.error(body.get('errmsg'))
        raise Exception(body.get('errmsg'))
    return body
