import argparse
from flask import Flask,request, make_response
from concurrent.futures import ThreadPoolExecutor

from wxcrypt import WXBizMsgCrypt
from wxsuite import Suite
from wxcrop import Crop
from wxmessage import xml2map
from handler import Handler
from log import logger

executor = ThreadPoolExecutor()

app=Flask(__name__)

def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--domain', '-d', type=str, help='your host')
    arg_parser.add_argument('--port', '-p', default=8075, type=int, help="port to build web server")
    arg_parser.add_argument('--suiteid', '-si', type=str, help='your suite id')
    arg_parser.add_argument('--secret', '-ss', type=str, help='your Secret')
    arg_parser.add_argument('--token', '-st', type=str, help='token set in suite app')
    arg_parser.add_argument('--aeskey', '-sk', type=str, help='encoding aeskey')
    arg_parser.add_argument('--gitlab_domain', '-gd', type=str, help='gitlab domain')
    arg_parser.add_argument('--gitlab_appid', '-gi', type=str, help='gitlab appid')
    arg_parser.add_argument('--gitlab_secret', '-gs', type=str, help='gitlab secret')

    return arg_parser.parse_args()
args = parse_args()

suite = Suite(args.domain, args.gitlab_domain, args.gitlab_appid, args.gitlab_secret, args.suiteid, args.secret)
crypt = WXBizMsgCrypt(args.token, args.aeskey, {args.suiteid, ''}).add_receive(suite.get_auth_crop_ids())

@app.route("/gitlab/oauth", methods=["GET", "POST"])
def oauth():
    crop_user_key = request.args.get('crop_user_key').split(">")
    crop_id = crop_user_key[0]
    user_key = crop_user_key[1]
    auth_code = request.args.get('code')
    crop = Crop(crop_id, suite)
    return crop.save_gitlab_auth_info(auth_code, request.args.get('crop_user_key'), user_key)


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
        return make_response({"errcode": ret}, 500)

    logger.info("start" + xml2map(xml).get('Content',''))
    handler = Handler(crypt, suite, action, xml2map(xml))
    executor.submit(handler.accept)
    logger.info("end" + xml2map(xml).get('Content',''))
    return make_response("success")



if __name__ == "__main__":
    app.run(debug=True, port=args.port)
