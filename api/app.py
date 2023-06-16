import argparse
import json
import datetime
from flask import Flask, request, make_response, jsonify
from flask_apscheduler import APScheduler
from concurrent.futures import ThreadPoolExecutor
from log import logger
from wxcrop import Crop
from handler import Handler
from task import Task
from redisclient import duplicate_correct_id
from wxmessage import xml2dirt
executor = ThreadPoolExecutor()
app = Flask(__name__)
scheduler = APScheduler()


class Config(object):
    SCHEDULER_API_ENABLED = True


def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--port', '-p', default=8075, type=int, help="port to build web server")
    arg_parser.add_argument('--crop_id', '-i', type=str, help='your crop id')
    arg_parser.add_argument('--crop_secret', '-s', type=str, help='your crop Secret')
    arg_parser.add_argument('--token', '-t', type=str, help='token set in crop app')
    arg_parser.add_argument('--aes_key', '-k', type=str, help='encode aes_key')
    return arg_parser.parse_args()


args = parse_args()
crop = Crop(args)
crypt = crop.get_crypt()
task = Task(True)
# crop.create_button()
# Task().clear_dirty_branch_notice(crop)


@app.route("/gitlab/hook", methods=["POST"])
def gitlab_hook():
    body = json.loads(request.data.decode('utf-8'))
    update_config = False
    for commit in body.get('commits'):
        if "config.yaml" in commit.get('modified', []):
            update_config = True
    if not update_config:
        return "not update version"
    branch = body.get('ref').rsplit("/", 1)[1]
    executor.submit(Task().check_version, branch, crop)
    return make_response("success")


@app.route("/listener/deploy", methods=["POST"])
def listener_deploy():
    body = json.loads(request.data.decode('utf-8'))
    logger.info("listener_deploy:" + str(body))
    deploy_ret = body.get("ret")
    if deploy_ret is None:
        return make_response("ignore")
    if deploy_ret not in ["success", "成功"]:
        return make_response("ignore")
    deploy_group = set(body.get("project_group").split(","))
    if deploy_group is None:
        return make_response("ignore")
    modules = deploy_group.intersection({"apps", "global", "web", "trek", "h5", "front-theory", "front-goserver"})
    if len(modules) < 1:
        return make_response("ignore")
    branches = body.get("branch", body.get("project_desc")).split(",")
    clusters = body.get("cluster").split(",")
    ret = Task().build_branch_task(branches, modules, clusters, crop)
    return make_response(ret)


@app.route("/branch/clear", methods=["GET"])
def branch_clear():
    user_id = request.args.get('user_id')
    branch = request.args.get('branch')
    executor.submit(Task().clear_dirty_branch, user_id, branch, crop)
    return make_response("success")


@app.route("/branch/correct", methods=["GET"])
def branch_correct():
    try:
        correct_id = request.args.get('correct_id')
        user_id = request.args.get('user_id')
        branch = request.args.get('branch')
        project = request.args.get('project')
        if duplicate_correct_id(correct_id, branch, project):
            raise Exception("请不要重复校正版本号")
        executor.submit(Task().branch_correct, user_id, branch, project, crop)
        return make_response("success")
    except Exception as err:
        logger.exception(err)
        return make_response(str(err))


@app.route("/branch/seal", methods=["POST"])
def branch_seal():
    response = {}
    try:
        body = json.loads(request.data.decode('utf-8'))
        logger.info("branch_seal:" + str(body))
        response = Task().branch_seal(body)
    except Exception as err:
        logger.exception(err)
        response["ret"] = False
        response["msg"] = str(err)
    return jsonify(response)


@app.route("/branch/release/check", methods=["POST"])
def branch_release_check():
    response = {}
    try:
        body = json.loads(request.data.decode('utf-8'))
        logger.info("release_check:" + str(body))
        response["ret"] = True
        response["msg"] = Task().release_check(body)
    except Exception as err:
        logger.exception(err)
        response["ret"] = False
        response["msg"] = str(err)
    return jsonify(response)


@scheduler.task('cron', id='job_check_version', week='*', day_of_week='0-6',
                hour='8-22', minute='0', timezone='Asia/Shanghai')
def job_check_version():
    cur_time = datetime.datetime.now()
    branch = 'sprint' + cur_time.strftime('%Y%m%d')
    task.check_version(branch, crop)


@scheduler.task('interval', id='job_mr_request_notify', seconds=60,
                timezone='Asia/Shanghai', max_instances=4)
def job_mr_request_notify():
    task.send_mr_notify(crop)


@app.route("/callback/<action>", methods=["GET"])
def verify(action: str):
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    echo_str = request.args.get('echostr')
    ret, echo_str = crypt.VerifyURL(msg_signature, timestamp, nonce, echo_str)
    return echo_str.decode('utf-8') if ret == 0 else "error"


@app.route("/callback/data", methods=["POST"])
def callback():
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    body = request.data.decode('utf-8')
    ret, raw = crypt.DecryptMsg(body, msg_signature, timestamp, nonce)
    if ret != 0:
        _error = {"errcode": ret, "message": "验证企业微信消息真实性失败"}
        return make_response(_error, 500)
    # 启用异步任务消费消息
    executor.submit(Handler(crop, xml2dirt(raw)).accept)
    return make_response("success")


@app.route("/check/upgrade", methods=["GET"])
def check_upgrade():
    version = request.args.get('version')
    new_version = task.get_upgrade_version()
    response = {"ret": True}
    if version != new_version:
        response["ret"] = False
    return jsonify(response)


# 接受编译结果通知
@app.route("/build/notify", methods=["GET"])
def build_notify():
    build_id = request.args.get('id')
    ret = request.args.get('ret')
    task.send_build_notify(crop, build_id, ret)
    return make_response("success")


if __name__ == "__main__":
    app.config.from_object(Config())
    # it is also possible to enable the API directly
    # scheduler.api_enabled = True
    scheduler.init_app(app)
    scheduler.start()
    app.run(host="0.0.0.0", debug=True, use_reloader=False, port=args.port)
