import time
import requests
import json
base = 'http://zentao.77hub.com/zentao/api.php/v1/'


def get_token(username, password):
    headers = {'Content-Type': 'application/json'}
    data = {"account": username, "password": password}
    response = requests.post(base + "tokens", headers=headers, data=json.dumps(data))
    print(response.status_code)
    if response.status_code == 200 or response.status_code == 201:
        print("访问成功")
        print(response.json())
        body = response.json()
        return body['token']


def create_task(context):
    headers = {
        'Content-Type': 'application/json',
        'Token': get_token('linrol.luo', 'Linrol19950120'),
    }
    contexts = context.split('@')
    task_name = contexts[1]
    task_cost = int(contexts[2])
    data = {
        "execution": 1955,
        "type": "devel",
        "module": 1379,
        "assignedTo": ["linrol.luo"],
        "pri": 3,
        "name": task_name,
        "desc": task_name,
        "estStarted": time.strftime("%Y-%m-%d"),
        "deadline": time.strftime("%Y-%m-%d"),
        "estimate": task_cost
    }
    response = requests.post(base + 'executions/1955/tasks', headers=headers, data=json.dumps(data))
    if response.status_code == 200 or response.status_code == 201:
        resp = response.json()
        return "任务创建成功【id:{}, name:{}】".format(resp['id'], resp['name'])
    else:
        return response.text

# create_task("禅道@自动化创建禅道任务@1")