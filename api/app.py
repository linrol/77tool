import argparse
import json
import datetime
from flask import Flask, request, make_response
from flask_apscheduler import APScheduler
from concurrent.futures import ThreadPoolExecutor
from log import logger
from wxcrop import Crop
from handler import Handler
from task import Task
executor = ThreadPoolExecutor()
app = Flask(__name__)
scheduler = APScheduler()


class Config(object):
    SCHEDULER_API_ENABLED = True


def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--env', '-e', default="prod", type=str,
                            help='your host')
    arg_parser.add_argument('--domain', '-d', type=str, help='your host')
    arg_parser.add_argument('--port', '-p', default=8075, type=int,
                            help="port to build web server")
    arg_parser.add_argument('--crop_id', '-i', type=str, help='your crop id')
    arg_parser.add_argument('--crop_secret', '-s', type=str,
                            help='your crop Secret')
    arg_parser.add_argument('--token', '-t', type=str,
                            help='token set in crop app')
    arg_parser.add_argument('--aes_key', '-k', type=str, help='encode aes_key')
    arg_parser.add_argument('--gitlab_domain', '-gd', type=str,
                            help='gitlab domain')
    arg_parser.add_argument('--gitlab_app_id', '-gi', type=str,
                            help='gitlab app_id')
    arg_parser.add_argument('--gitlab_secret', '-gs', type=str,
                            help='gitlab secret')
    return arg_parser.parse_args()


args = parse_args()
crop = Crop(args)
crypt = crop.get_crypt()
# crop.create_button()


@app.route("/gitlab/hook", methods=["GET", "POST"])
def gitlab_hook():
    body = json.loads(request.data.decode('utf-8'))
    update_config = False
    for commit in body.get('commits'):
        if "config.yaml" in commit.get('modified', []):
            update_config = True
    if not update_config:
        return "not update version"
    branch = body.get('ref').rsplit("/", 1)[1]
    duty_user_id, _ = crop.get_duty_info("backend", True)
    executor.submit(Task().check_version, 'LuoLin', branch, crop.send_text_msg)
    return make_response("success")


@scheduler.task('cron', id='job_check_version', week='*', day_of_week='2-6',
                hour='8-20', minute='0', timezone='Asia/Shanghai')
def job_check_version():
    cur_time = datetime.datetime.now()
    branch = 'sprint' + cur_time.strftime('%Y%m%d')
    Task().check_version('LuoLin', branch, crop.send_text_msg)


@app.route("/callback/<action>", methods=["GET"])
def verify(action: str):
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    echo_str = request.args.get('echostr')
    ret, echo_str = crypt.VerifyURL(msg_signature, timestamp, nonce, echo_str)
    if ret == 0:
        return echo_str.decode('utf-8')
    else:
        return "error"


@app.route("/callback/data", methods=["POST"])
def callback():
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    body = request.data.decode('utf-8')
    ret, raw_content = crypt.DecryptMsg(body, msg_signature, timestamp, nonce)
    if ret != 0:
        logger.error("验证企业微信消息真实性失败")
        return make_response({"errcode": ret}, 500)

    # 启用异步任务消费消息
    executor.submit(Handler(crypt, crop, raw_content).accept)
    return make_response("success")


if __name__ == "__main__":
    app.config.from_object(Config())
    # it is also possible to enable the API directly
    # scheduler.api_enabled = True
    scheduler.init_app(app)
    scheduler.start()

    app.run(debug=True, use_reloader=False, port=args.port)
