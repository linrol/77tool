import requests
import json
from log import logger

def post(url, params):
    response = requests.post(url, json.dumps(params))
    body = json.loads(response.text)
    if body.get('errcode', '0') != 0 and 'errmsg' in body:
        logger.error(body.get('errmsg'))
        raise Exception(body.get('errmsg'))
    return body