import argparse
import json
from datetime import datetime
from flask import Flask, request, make_response, jsonify, render_template
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
processes = []


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
task = Task(crop, True)
# crop.create_button()
# Task(crop).clear_dirty_branch_notice(crop)
@app.before_request
def before_request():
    global processes
    now_time = datetime.now().strftime("%Y%m%d%H%M%S")
    request.environ["date"] = now_time
    processes.append(request.environ["date"] + "_" + request.url)
@app.after_request
def after_request(response):
    global processes
    processes.remove(request.environ["date"] + "_" + request.url)
    return response
@app.route('/processes')
def is_processing():
    return jsonify(processes=processes)

# gitlab代码提交hook
@app.route("/gitlab/hook", methods=["POST"])
def gitlab_hook():
    body = json.loads(request.data.decode('utf-8'))
    update_config = False
    author_id = None
    for commit in body.get('commits'):
        if "config.yaml" in commit.get('modified', []):
            update_config = True
            author_id = body.get('user_username')
            break
    if not update_config:
        return "not update version"
    branch = body.get('ref').rsplit("/", 1)[1]
    executor.submit(task.check_version, branch, author_id)
    return make_response("success")

# 发布结果监听，触发代码合并
@app.route("/listener/deploy", methods=["POST"])
def listener_deploy():
    body = json.loads(request.data.decode('utf-8'))
    logger.info("listener_deploy:" + str(body))
    deploy_ret = body.get("ret")
    if deploy_ret is None:
        return make_response("ignore")
    if deploy_ret not in ["success", "成功"]:
        return make_response("ignore")
    groups = set(body.get("project_group").split(","))
    if groups is None:
        return make_response("ignore")
    if "idps" in groups:
        groups.add("qip-front")
    if "openapi" in groups:
        groups.add("openapi-doc")
    branches = body.get("branch", body.get("project_desc")).split(",")
    cluster_ids = set(body.get("clusterId").split(","))
    cluster_str = body.get("cluster")
    ret = Task(crop).build_merge_task(branches, groups, cluster_str, cluster_ids)
    ret_msg = ";\n".join(ret)
    logger.info(ret_msg)
    return make_response(ret_msg)

# 分支清理
@app.route("/branch/clear", methods=["GET"])
def branch_clear():
    user_id = request.args.get('user_id')
    branch = request.args.get('branch')
    executor.submit(Task(crop).clear_dirty_branch, user_id, branch)
    return make_response("success")

# 分支版本号矫正
@app.route("/branch/correct", methods=["GET"])
def branch_correct():
    try:
        correct_id = request.args.get('correct_id')
        user_id = request.args.get('user_id')
        branch = request.args.get('branch')
        project = request.args.get('project')
        if duplicate_correct_id(correct_id, branch, project):
            raise Exception("请不要重复校正版本号")
        executor.submit(Task(crop).branch_correct, user_id, branch, project)
        return make_response("success")
    except Exception as err:
        logger.exception(err)
        return make_response(str(err))

# 分支封板操作
@app.route("/branch/seal", methods=["POST"])
def branch_seal():
    response = {}
    try:
        body = json.loads(request.data.decode('utf-8'))
        logger.info("branch_seal:" + str(body))
        response = Task(crop).branch_seal(body)
    except Exception as err:
        logger.exception(err)
        response["ret"] = False
        response["msg"] = str(err)
    return jsonify(response)

# 后端是否为发布包检查
@app.route("/branch/release/check", methods=["POST"])
def branch_release_check():
    response = {}
    try:
        body = json.loads(request.data.decode('utf-8'))
        logger.info("release_check:" + str(body))
        response["ret"] = True
        response["msg"] = Task(crop).release_check(body)
    except Exception as err:
        logger.exception(err)
        response["ret"] = False
        response["msg"] = str(err)
    return jsonify(response)

# 前端多列表方案预制restful接口
@app.route("/data/pre", methods=["POST"])
def front_data_pre():
    response = {}
    try:
        body = json.loads(request.data.decode('utf-8'))
        logger.info("front_data_pre:" + str(body))
        response["ret"] = True
        response["msg"] = Task(crop).front_data_pre(body)
    except Exception as err:
        logger.exception(err)
        response["ret"] = False
        response["msg"] = str(err)
    return jsonify(response)

# MR定时任务
@scheduler.task('interval', id='job_mr_request_notify', seconds=60, timezone='Asia/Shanghai', max_instances=4)
def job_mr_request_notify():
    task.send_mr_notify()

# 应用消息消费回调
@app.route("/callback/<action>", methods=["GET"])
def verify(action: str):
    msg_signature = request.args.get('msg_signature')
    timestamp = request.args.get('timestamp')
    nonce = request.args.get('nonce')
    echo_str = request.args.get('echostr')
    ret, echo_str = crypt.VerifyURL(msg_signature, timestamp, nonce, echo_str)
    return echo_str.decode('utf-8') if ret == 0 else "error"

# 应用消息消费回调
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

# 分支管理工具强制更新检查
@app.route("/check/upgrade", methods=["GET"])
def check_upgrade():
    version = request.args.get('version')
    new_version = task.get_upgrade_version()
    response = {"ret": True}
    if version != new_version:
        response["ret"] = False
    return jsonify(response)

# 消费ops编译结果通知
@app.route("/build/notify", methods=["GET"])
def build_notify():
    build_id = request.args.get('id')
    ret = request.args.get('ret')
    task.send_build_notify(build_id, ret)
    return make_response("success")

# 更新应用信息
@app.route("/app/update", methods=["POST"])
def app_update():
    body = json.loads(request.data.decode('utf-8'))
    name = body.get('name')
    notify = body.get('notify')
    notify_msg = body.get('notify_msg')
    task.app_update(name, notify, notify_msg)
    return make_response("success")

@app.route("/version/compare")
def version_compare():
    return render_template("version.html")

@app.route("/version/data", methods=["POST"])
def version_data():
    body = json.loads(request.data.decode('utf-8'))
    return jsonify(task.version_data(body.get("bs")))


if __name__ == "__main__":
    app.config.from_object(Config())
    # it is also possible to enable the API directly
    # scheduler.api_enabled = True
    scheduler.init_app(app)
    scheduler.start()
    # vue 语法{{}}冲突
    app.jinja_options = {'variable_start_string': '{{{', 'variable_end_string': '}}}'}
    app.run(host="0.0.0.0", debug=True, use_reloader=False, port=args.port)
