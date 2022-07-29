#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------File Info-----------------------
Name: web.py
Description: web api support
Author: GentleCP
Email: me@gentlecp.com
Create Date: 2021/6/19
-----------------End-----------------------------
"""
import argparse
import requests
from fastapi import FastAPI
from fastapi import Response, Request
from WXBizMsgCrypt3 import WXBizMsgCrypt
from xml.etree.ElementTree import fromstring
from redis import Redis,ConnectionPool
import json
import time
import uvicorn

app = FastAPI()

#连接池
redis_pool = ConnectionPool(host="linrol.cn",port=6379,password="linrol_redis",db=0,decode_responses=True,max_connections=16)
client = Redis(connection_pool=redis_pool)

def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--port', '-p', default=8000, type=int, help="port to build web server")
    arg_parser.add_argument('--token', '-t', type=str, help='token set in corpwechat app')
    arg_parser.add_argument('--aeskey', '-a', type=str, help='encoding aeskey')
    arg_parser.add_argument('--suiteid', '-s', type=str, help='your suite id')
    args = arg_parser.parse_args()
    return args

args = parse_args()
receive_id_set = {args.suiteid}
auth_corpid = client.hget('wechat-work-' + args.suiteid, 'auth_corpid')
for c in auth_corpid.split(','):
    receive_id_set.add(c)
wxcpt = WXBizMsgCrypt(args.token, args.aeskey, receive_id_set)



@app.get("/callback/{action}")
async def verify(action: str,
                 msg_signature: str,
                 timestamp: str,
                 nonce: str,
                 echostr: str):
    ret, sEchoStr = wxcpt.VerifyURL(msg_signature, timestamp, nonce, echostr)
    if ret == 0:
        content=sEchoStr.decode('utf-8')
        return Response(content)
    else:
        print(sEchoStr)

@app.post("/callback/{action}")
async def recv(action: str,
    msg_signature: str,
    timestamp: str,
    nonce: str,
    request: Request):
    body = await request.body()
    ret, sMsg = wxcpt.DecryptMsg(body.decode('utf-8'), msg_signature, timestamp, nonce)
    decrypt_data = {}
    for node in list(fromstring(sMsg.decode('utf-8'))):
        decrypt_data[node.tag] = node.text

    if action == "command":
        return handle_command(decrypt_data)
    if action == "data":
        return handle_data(decrypt_data, nonce)

def handle_command (decrypt_data):
    into_type = decrypt_data.get('InfoType', '')
    suite_id = decrypt_data.get('SuiteId')
    suite_key = 'wechat-work-' + suite_id
    if into_type == 'suite_ticket':
        suite_ticket = decrypt_data.get('SuiteTicket')
        client.hmset(suite_key, {'suite_ticket': suite_ticket})
        save_suite_access_token(suite_key, suite_id, suite_ticket)
    if into_type == 'create_auth':
        auth_code = decrypt_data.get('AuthCode')
        client.hmset(suite_key, {"auth_code": auth_code})
        save_permanent_code(suite_key)
    return Response(content="success")

def save_suite_access_token (suite_key, suite_id, suite_ticket):
    token_expire = client.hget(suite_key, 'token_expire')
    if (token_expire is not None):
        if int(time.time()) - int(token_expire) < 3600:
            return
    suite_secret = client.hget(suite_key, 'suite_secret')
    url = 'https://qyapi.weixin.qq.com/cgi-bin/service/get_suite_token'
    params = json.dumps({'suite_id': suite_id, 'suite_secret': suite_secret, 'suite_ticket': suite_ticket})
    response = requests.post(url, data=params)
    suite_access_token = json.loads(response.text).get('suite_access_token', None)
    if suite_access_token is not None:
        client.hmset(suite_key, {"suite_access_token": suite_access_token})
        client.hmset(suite_key, {"token_expire": int(time.time())})

def save_permanent_code (suite_key):
    suite_access_token = client.hget(suite_key, 'suite_access_token')
    auth_code = client.hget(suite_key, 'auth_code')
    url = 'https://qyapi.weixin.qq.com/cgi-bin/service/get_permanent_code?suite_access_token=' + suite_access_token
    params = json.dumps({'auth_code': auth_code})
    response = json.loads(requests.post(url, data=params).text)
    if 'errcode' in response.keys():
        return
    corpid = response.get('auth_corp_info').get('corpid')
    permanent_code = response.get('permanent_code')
    corp_key = 'wechat-work-' + corpid
    client.hmset(corp_key, {"permanent_code": permanent_code})

    auth_corpid = client.hget(suite_key, 'auth_corpid')
    if auth_corpid is not None and corpid in auth_corpid:
        return
    auth_corpid = corpid if auth_corpid is None else corpid + ',' + auth_corpid
    client.hmset(suite_key, {"auth_corpid": auth_corpid})

def handle_data (decrypt_data, nonce):
    ret, params = build_text_response(decrypt_data, nonce, "hello word")
    if ret == 0:
        return Response(content=params)
    else:
        print(params)

def build_text_response(decrypt_data, nonce, context):
    sRespData = """<xml><ToUserName>{to_username}</ToUserName><FromUserName>{from_username}</FromUserName><CreateTime>{create_time}</CreateTime><MsgType>text</MsgType><Content>{content}</Content></xml>""" \
        .format(to_username=decrypt_data['ToUserName'],
                from_username=decrypt_data['FromUserName'],
                create_time=decrypt_data['CreateTime'],
                content=context)
    return wxcpt.EncryptMsg(sReplyMsg=sRespData, sNonce=nonce, coverReceiveId=decrypt_data['ToUserName'])

if __name__ == "__main__":
    uvicorn.run("web:app", port=args.port, host='0.0.0.0', reload=False)
