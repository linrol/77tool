#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------File Info-----------------------
Name: api.py
Description: web api support
Author: GentleCP
Email: me@gentlecp.com
Create Date: 2021/6/19
-----------------End-----------------------------
"""
from fastapi import FastAPI
from fastapi import Response, Request
import argparse
import uvicorn
import asyncio

from wxcrypt import WXBizMsgCrypt
from wxsuite import Suite
from wxmessage import xml2map
from handler import Handler
from log import logger


app = FastAPI()

def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--port', '-p', default=8000, type=int, help="port to build web server")
    arg_parser.add_argument('--token', '-t', type=str, help='token set in corpwechat app')
    arg_parser.add_argument('--aeskey', '-a', type=str, help='encoding aeskey')
    arg_parser.add_argument('--suiteid', '-i', type=str, help='your suite id')
    arg_parser.add_argument('--secret', '-s', type=str, help='your Secret')
    return arg_parser.parse_args()

args = parse_args()

receive_id_set = {args.suiteid}
suite = Suite(args.suiteid, args.secret)
auth_corps = suite.get_auth_corps()
if auth_corps is not None:
  for c in auth_corps.split(','):
    receive_id_set.add(c)
crypt = WXBizMsgCrypt(args.token, args.aeskey, receive_id_set)

@app.get("/callback/{action}")
async def verify(msg_signature: str,timestamp: str,nonce: str, echostr: str):
    ret, echo_str = crypt.VerifyURL(msg_signature, timestamp, nonce, echostr)
    if ret == 0:
        return Response(echo_str.decode('utf-8'))
    else:
        logger.error(echo_str)

@app.post("/callback/{action}")
async def recv(action: str,msg_signature: str,timestamp: str,nonce: str,request: Request):
    body = (await request.body()).decode('utf-8')
    ret, xml = crypt.DecryptMsg(body, msg_signature, timestamp, nonce)
    if ret != 0:
        return
    handler = Handler(crypt, suite, action, xml2map(xml))
    asyncio.create_task(handler.accept())
    return Response("success")


if __name__ == "__main__":
    uvicorn.run("api:app", port=args.port, host='0.0.0.0', reload=False)
