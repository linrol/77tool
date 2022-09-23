import re
from redisclient import get_branch_mapping

menu_help = {
  "data_pre_new": ">**新列表方案（固定值不要删除）** " 
                  "\n>环　境：<font color=\"comment\">输入预制数据来源环境，例：temp1</font>" 
                  "\n>租　户：<font color=\"comment\">输入预制数据来源租户，例：47L0LP505840001</font>" 
                  "\n>分　支：<font color=\"comment\">输入预制的代码分支，例：feature-purchase-budget</font>" 
                  "\n>列表组：<font color=\"comment\">输入列表方案组名称，例：Budget_Plan_Change_list,ProjectList</font>" 
                  "\n>合并人：<font color=\"comment\">输入分支有权限合并者人姓名，例：罗林</font>" 
                  "\n>" 
                  "\n>复制本模版，修改后回复我，预制成功后将会消息通知" 
                  "\n>或点击[去小程序操作](https://work.weixin.qq.com)",
  "data_pre_old": ">**老列表方案（固定值不要删除）** " 
                  "\n>环　境：<font color=\"comment\">输入预制数据来源环境，例：temp1</font>" 
                  "\n>租　户：<font color=\"comment\">输入预制数据来源租户，例：47L0LP505840001</font>" 
                  "\n>分　支：<font color=\"comment\">输入预制的代码分支，例：feature-purchase-budget</font>" 
                  "\n>列表组：<font color=\"comment\">输入列表方案组名称，例：Budget_Plan_Change_list</font>" 
                  "\n>合并人：<font color=\"comment\">输入分支有权限合并者人姓名，例：罗林</font>" 
                  "\n>" 
                  "\n>复制本模版，修改后回复我，预制成功后将会消息通知" 
                  "\n>或点击[去小程序操作](https://work.weixin.qq.com)",
  "branch_create": ">**拉分支（固定值不要删除）** " 
                   "\n>来源分支：<font color=\"comment\">输入基于哪个分支拉取，例：stage</font>" 
                   "\n>目标分支：<font color=\"comment\">输入拉取后的分支名称，例：sprint20220818</font>" 
                   "\n>工程模块：<font color=\"comment\">输入需要拉模块或工程，例：app-common,budget,project-api</font>" 
                   "\n>复制本模版，修改后回复我，拉取成功后将会消息通知" 
                   "\n>或点击[去小程序操作](https://work.weixin.qq.com)",
  "build_release_package": ">**构建发布包（固定值不要删除）** "
                           "\n>目标分支：<font color=\"comment\">输入需要构建发布包的分支名称，例：sprint20220818</font>"
                           "\n>模块类型：<font color=\"comment\">输入需要构建发布包的模块类型，例：all,global,apps(单选值)</font>"
                           "\n>前端预制：<font color=\"comment\">输入需要替换的front-apps.reimburse版本号，前端值班提供(此参数可空)</font>"
                           "\n>立即编译：<font color=\"comment\">输入需要构建发布包后是否立即编译，例：true,false(单选值)</font>"
                           "\n>或点击[去小程序操作](https://work.weixin.qq.com)"
}

msg = {
  "touser": "",
  "msgtype": "",
  "agentid": ""
}

msg_content = {
    "oauth_text_msg": "首次使用，请先进行gitlab身份认证\n复制链接{}在浏览器中打开\n或点击<a href=\"{}\">去授权</a>",
    "create_branch_task": {
        "card_type": "button_interaction",
        "source": {
            "desc": "值班助手",
            "desc_color": 1
        },
        "main_title": {
            "title": "值班助手-来自{}的拉分支请求"
        },
        "sub_title_text": "请确认以下信息，同意后自动拉取分支并修改版本号",
        "horizontal_content_list": [
            {
                "type": 3,
                "keyname": "发起人",
                "value": "龚建平",
                "userid": "LuoLin"
            },
            {
                "keyname": "来源分支",
                "value": "stage",
            },
            {
                "keyname": "目标分支",
                "value": "sprint20220818"
            },
            {
                "keyname": "工程模块",
                "value": "project，budget，app-common"
            }
        ],
        "task_id": "",
        "button_list": [
            {
                "text": "拒绝",
                "style": 3,
                "key": "deny@"
            },
            {
                "text": "同意",
                "style": 2,
                "key": "agree@"
            }
        ]
    },
    "change_branch_version": {
        "card_type": "button_interaction",
        "source": {
            "desc": "值班助手",
            "desc_color": 1
        },
        "main_title": {
            "title": "值班助手-版本号矫正任务"
        },
        "sub_title_text": "监控到以下目标分支版本号异常(小于基准分支版本号)，同意后将自动矫正版本号",
        "horizontal_content_list": [
            {
                "keyname": "基准分支",
                "value": "stage",
            },
            {
                "keyname": "目标分支",
                "value": "sprint20220818"
            },
            {
                "keyname": "监控信息",
                "value": "project，budget，app-common"
            }
        ],
        "task_id": "",
        "button_list": [
            {
                "text": "拒绝",
                "style": 3,
                "key": "deny@"
            },
            {
                "text": "同意",
                "style": 2,
                "key": "agree@"
            }
        ]
    },
    "create_branch_task_response": "本次拉取分支的任务已发送到值班人：{}，请等待值班审批同意后将开始执行"
}
build_group_mapping = {"all": ['framework', 'enterprise', 'enterprise-apps', 'enterprise-apps-api', 'global-apps', 'global-apps-api'],
                       "global": ['framework', 'global-apps', 'global-apps-api'],
                       "apps": ['framework', 'enterprise', 'enterprise-apps', 'enterprise-apps-api']
                       }

target_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'

import unicodedata as ucd
from xml.etree.ElementTree import fromstring

def xml2dirt(raw_xml):
    data = {}
    for node in list(fromstring(raw_xml.decode('utf-8'))):
        data[node.tag] = node.text
    return data

def is_chinese(k, word):
    for ch in word:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

def get_map(lines, filter_chinese=True):
    map = {}
    for line in lines:
        line = ucd.normalize('NFKC', line)
        separator = ":" if ":" in line else "："
        kv = line.replace(" ", "").split(separator)
        if len(kv) != 2:
            continue
        k = kv[0]
        v = kv[1]
        if k == '' or v == '':
            continue
        if filter_chinese and is_chinese(k, v):
            continue
        map[k] = v
    return map

def get_pre_dirt(msg_content):
    pre_data_map = get_map(msg_content.split('\n'))
    require_keys = {"环境", "租户", "分支", "列表组"}.difference(pre_data_map.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    tenant_id = "tenant" + pre_data_map.get('租户')
    return pre_data_map.get('环境'), tenant_id, pre_data_map.get('分支'), pre_data_map.get('列表组'), pre_data_map.get("合并人", None)

def get_branch_dirt(msg_content):
    branch_map = get_map(msg_content.split('\n'))
    require_keys = {"来源分支", "目标分支", "工程模块"}.difference(branch_map.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    return branch_map.get('来源分支'), branch_map.get('目标分支'), branch_map.get('工程模块')

def get_init_feature_dirt(msg_content):
    init_feature = get_map(msg_content.split('\n'), False)
    require_keys = {"来源分支", "目标分支", "分支版本", "分支管理"}.difference(init_feature.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    return init_feature

def get_build_dirt(msg_content):
    branch_map = get_map(msg_content.split('\n'))
    require_keys = {"目标分支", "立即编译"}.difference(branch_map.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    target_branch = branch_map.get('目标分支')
    target_name = None
    target_date = None
    mapping = get_branch_mapping()
    if re.search(target_branch, target_regex):
        target_date = re.search(target_branch, target_regex).group()
        target_name = target_branch.replace(target_date, "")
    if target_date is None or target_name not in ",".join(mapping.values()):
        raise Exception("目标分支非值班系列【{}】".format(",".join(mapping.values())))
    group = branch_map.get('模块类型', 'all')
    if group not in build_group_mapping.keys():
        raise Exception("模块类型异常，必须是all,global,apps其中之一")
    is_build = branch_map.get('立即编译') == 'true'
    front_version = branch_map.get("前端预制", '').strip()
    group_list = build_group_mapping.get(group).copy()
    if len(front_version) > 0:
        group_list.append("front-apps:reimburse={}".format(front_version))
    if group != 'all':
        path = ".{}@{}".format(group, "platform")
    else:
        path = None
    return branch_map.get('目标分支'), group_list, path, is_build

def build_create_branch__msg(req_user_id, req_user_name, duty_user_name, task_id, source, target, project_names):
    task_info_list = [{
        "type": 3,
        "keyname": "申请人",
        "value": req_user_name,
        "userid": req_user_id
    }, {
        "keyname": "来源分支",
        "value": source,
    }, {
        "keyname": "目标分支",
        "value": target,
    }, {
        "keyname": "工程模块",
        "value": project_names,
    }]
    msg_content["create_branch_task"]["main_title"]["title"] = "值班助手-来自{}的拉分支请求".format(req_user_name)
    msg_content["create_branch_task"]["horizontal_content_list"] = task_info_list
    msg_content["create_branch_task"]["task_id"] = task_id
    msg_content["create_branch_task"]["button_list"][0]["key"] = "deny@" + task_id
    msg_content["create_branch_task"]["button_list"][1]["key"] = "agree@" + task_id
    return msg_content["create_branch_task"], str(msg_content["create_branch_task_response"].format(duty_user_name))

def build_change_branch_version_msg(task_id, source, target, project_info):
    task_info_list = [{
        "keyname": "基准分支",
        "value": source,
    }, {
        "keyname": "目标分支",
        "value": target,
    }, {
        "keyname": "监控信息",
        "value": project_info,
    }]
    msg_content["change_branch_version"]["horizontal_content_list"] = task_info_list
    msg_content["change_branch_version"]["task_id"] = task_id
    msg_content["change_branch_version"]["button_list"][0]["key"] = "deny@" + task_id
    msg_content["change_branch_version"]["button_list"][1]["key"] = "agree@" + task_id
    return msg_content["change_branch_version"]