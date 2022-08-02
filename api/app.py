import argparse
from flask import Flask,request, make_response
from concurrent.futures import ThreadPoolExecutor

from wxcrypt import WXBizMsgCrypt
from wxsuite import Suite
from wxmessage import xml2map
from handler import Handler
from log import logger

executor = ThreadPoolExecutor()

app=Flask(__name__)

def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--port', '-p', default=8000, type=int, help="port to build web server")
    arg_parser.add_argument('--token', '-t', type=str, help='token set in corpwechat app')
    arg_parser.add_argument('--aeskey', '-a', type=str, help='encoding aeskey')
    arg_parser.add_argument('--suiteid', '-i', type=str, help='your suite id')
    arg_parser.add_argument('--secret', '-s', type=str, help='your Secret')
    return arg_parser.parse_args()
args = parse_args()
crypt = WXBizMsgCrypt(args.token, args.aeskey, { args.suiteid, ''})
suite = Suite(args.suiteid, args.secret)
suite.init_crypt_received(crypt)

@app.route("/callback/<action>", methods=["GET"])
def verify(action: str):
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    echostr = request.args.get('echostr')
    ret, echo_str = crypt.VerifyURL(msg_signature, timestamp, nonce, echostr)
    if ret == 0:
        return echo_str.decode('utf-8')
    else:
        return "error"

@app.route("/callback/<action>",methods=["POST"])
def recv(action: str):
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    body = request.data.decode('utf-8')
    ret, xml = crypt.DecryptMsg(body, msg_signature, timestamp, nonce)
    if ret != 0:
        return make_response({"errcode":ret}, 500)

    logger.info("start" + xml2map(xml).get('Content',''))
    handler = Handler(crypt, suite, action, xml2map(xml))
    executor.submit(handler.accept)
    logger.info("end" + xml2map(xml).get('Content',''))
    return make_response("success")

if __name__ == "__main__":
    app.run(debug=True, port=args.port)