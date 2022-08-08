import argparse
from flask import Flask, request, make_response
from concurrent.futures import ThreadPoolExecutor

from wxcrop import Crop
from wxmessage import xml2map
from handler import Handler

executor = ThreadPoolExecutor()

app=Flask(__name__)

def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--domain', '-d', type=str, help='your host')
    arg_parser.add_argument('--port', '-p', default=8075, type=int, help="port to build web server")
    arg_parser.add_argument('--crop_id', '-i', type=str, help='your crop id')
    arg_parser.add_argument('--crop_secret', '-s', type=str, help='your crop Secret')
    arg_parser.add_argument('--token', '-t', type=str, help='token set in crop app')
    arg_parser.add_argument('--aeskey', '-k', type=str, help='encoding aeskey')
    arg_parser.add_argument('--gitlab_domain', '-gd', type=str, help='gitlab domain')
    arg_parser.add_argument('--gitlab_app_id', '-gi', type=str, help='gitlab appid')
    arg_parser.add_argument('--gitlab_secret', '-gs', type=str, help='gitlab secret')

    return arg_parser.parse_args()
args = parse_args()

crop = Crop(args)
crypt = crop.get_crypt()
# crop.create_button()

@app.route("/gitlab/oauth", methods=["GET", "POST"])
def oauth():
    user_key = request.args.get('user_key')
    auth_code = request.args.get('code')
    return crop.save_gitlab_auth_info(auth_code, user_key)


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

    handler = Handler(crypt, crop, action, xml2map(xml))
    executor.submit(handler.accept)
    return make_response("success")

if __name__ == "__main__":
    app.run(debug=True, port=args.port)
