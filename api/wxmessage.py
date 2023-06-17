import re
import xmltodict
import unicodedata as ucd
from redisclient import get_branch_mapping

menu_help = {
  "data_pre_new": ">**新列表方案（固定值不要删除）** " 
                  "\n>环　境：<font color=\"comment\">输入预制数据来源环境，例：temp1</font>" 
                  "\n>租　户：<font color=\"comment\">输入预制数据来源租户，例：47L0LP505840001</font>" 
                  "\n>分　支：<font color=\"comment\">输入预制的代码分支，例：feature-purchase-budget</font>" 
                  "\n>列表组：<font color=\"comment\">输入列表方案组名称，例：Budget_Plan_Change_list,ProjectList</font>" 
                  "\n>合并人：<font color=\"comment\">输入分支有权限合并者人姓名，例：罗林</font>" 
                  "\n>" 
                  "\n>修改本模版后发送，预制成功后将会消息通知" 
                  "\n>或点击[去小程序操作](https://work.weixin.qq.com)",
  "data_pre_old": ">**老列表方案（固定值不要删除）** " 
                  "\n>环　境：<font color=\"comment\">输入预制数据来源环境，例：temp1</font>" 
                  "\n>租　户：<font color=\"comment\">输入预制数据来源租户，例：47L0LP505840001</font>" 
                  "\n>分　支：<font color=\"comment\">输入预制的代码分支，例：feature-purchase-budget</font>" 
                  "\n>列表组：<font color=\"comment\">输入${entityName}.${listName}，例：AssetSplit.global-search-list</font>" 
                  "\n>合并人：<font color=\"comment\">输入分支有权限合并者人姓名，例：罗林</font>" 
                  "\n>" 
                  "\n>修改本模版后发送，预制成功后会消息通知" 
                  "\n>或点击[去小程序操作](https://work.weixin.qq.com)",
  "branch_create": ">**<font color=\"info\">拉分支（固定值不要删除）</font>** " 
                   "\n>来源分支：<font color=\"comment\">输入基于哪个分支拉取，例：stage</font>" 
                   "\n>目标分支：<font color=\"comment\">输入拉取后的分支名称，例：sprint20220818</font>" 
                   "\n>工程模块：<font color=\"comment\">输入需要拉模块或工程，例：app-common,budget,front-theory</font>"
                   "\n><font color=\"warning\">功能说明，基于来源分支创建目标分支的工程模块，根据权重、系数和偏移量计算更新目标分支版本号</font>",
  "branch_move": ">**<font color=\"info\">分支迁移（固定值不要删除）</font>** "
                 "\n>迁移分支：<font color=\"comment\">输入需要迁移的分支名称，例：sprint20220818</font>"
                 "\n>迁出分支：<font color=\"comment\">输入需要迁出的分支名称，例：stage-global</font>"
                 "\n>迁移模块：<font color=\"comment\">输入需要迁移的工程模块，例：global</font>"
                 "\n><font color=\"warning\">功能说明，将迁移分支备份至迁出分支，并删除迁移分支的工程模块</font>",
  "branch_merge": ">**<font color=\"info\">分支合并（固定值不要删除）</font>** "
                   "\n>来源分支：<font color=\"comment\">输入将被合并的分支名称，例：sprint20220818</font>"
                   "\n>目标分支：<font color=\"comment\">输入需要合并至的分支名称，例：stage</font>"
                   "\n>工程模块：<font color=\"comment\">输入需要合并的模块或工程，例：front-theory,front-goserver,apps,global</font>"
                   "\n>删除来源：<font color=\"comment\">分支合并成功后是否删除来源分支，例：true,false(单选值)</font>"
                   "\n><font color=\"warning\">功能说明，将来源分支合并至目标分支，预检测存在冲突将放弃合并</font>",
  "branch_protect": ">**<font color=\"info\">分支保护（固定值不要删除）</font>** "
                    "\n>目标分支：<font color=\"comment\">输入将被保护的分支名称，例：sprint20220818</font>"
                    "\n>工程模块：<font color=\"comment\">输入要保护的工程或模块，例：front-theory,front-goserver</font>"
                    "\n>是否保护：<font color=\"comment\">保护或取消保护分支，例：true,false(单选值)</font>"
                    "\n><font color=\"warning\">功能说明，将目标分支对应的工程模块分支保护或取消保护</font>",
  "build_release_package": ">**<font color=\"info\">构建发布包（固定值不要删除）</font>** "
                           "\n>目标分支：<font color=\"comment\">输入需要构建发布包的分支名称，例：sprint20220818</font>"
                           "\n>构建模块：<font color=\"comment\">输入需要构建发布包的模块，例：all,global,apps(单选值)</font>"
                           "\n>前端预制：<font color=\"comment\">输入需要替换的front-apps.reimburse版本号，前端值班提供(此参数可空)</font>"
                           "\n>立即编译：<font color=\"comment\">构建发布包后是否立即编译，例：true,false(单选值)</font>"
                           "\n><font color=\"warning\">功能说明，将目标分支的对应的工程模块构建release包并对分支封板</font>"
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
    "merge_branch_task": {
        "card_type": "button_interaction",
        "source": {
            "desc": "值班助手",
            "desc_color": 1
        },
        "main_title": {
            "title": "值班助手-代码合并任务"
        },
        "sub_title_text": "检测到{}分支已发布到{}，同意后将开始合并代码",
        "horizontal_content_list": [
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
                "value": "apps,global"
            }
        ],
        "button_selection": {
            "question_key": "remove_source",
            "title": "删除来源",
            "option_list": [
                {
                    "id": "true",
                    "text": "是"
                },
                {
                    "id": "false",
                    "text": "否"
                }
            ],
            "selected_id": "btn_selection_id1"
        },
        "task_id": "",
        "button_list": [
            {
                "text": "取消",
                "style": 3,
                "key": "deny@"
            },
            {
                "text": "合并",
                "style": 2,
                "key": "agree@"
            }
        ]
    },
    "move_branch_task": {
        "card_type": "button_interaction",
        "source": {
            "desc": "值班助手",
            "desc_color": 1
        },
        "main_title": {
            "title": "值班助手-分支迁移任务"
        },
        "sub_title_text": "检测到{}分支已发布到{}，同意后将开始迁移模块",
        "horizontal_content_list": [
            {
                "keyname": "来源分支",
                "value": "stage",
            },
            {
                "keyname": "目标分支",
                "value": "sprint20220818"
            },
            {
                "keyname": "迁移模块",
                "value": "global"
            }
        ],
        "task_id": "",
        "button_list": [
            {
                "text": "取消",
                "style": 3,
                "key": "deny@"
            },
            {
                "text": "迁移",
                "style": 2,
                "key": "agree@"
            }
        ]
    },
    "create_branch_task_response": "本次拉取分支的任务已发送到负责人：{}，请等待值班审批同意后将开始执行",
    "build_ret": "您触发的独立编译任务ID:{}完成，编译结果：{}",
    "mr_source": "{}\n您发起的工程：{} MR请求，已被{}合并！\n已触发独立编译任务ID:{}，请自行关注编译结果",
    "mr_target": "您收到来自{}的MR请求，请及时合并！\n标题：{}\n工程/分支：{}(分支{}合并到{})\n{}",
    "merge_branch_result": "【代码合并通知】\n来源分支：{}\n目标分支：{}\n合并模块：{}\n合并结果：{}\n操  作  人：{}"
}
target_regex = r'20[2-9][0-9][0-1][0-9][0-3][0-9]$'


def xml2dirt(raw_xml):
    data = xmltodict.parse(raw_xml).get("xml")
    return data


def is_chinese(word):
    for ch in word:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False


def get_map(lines, filter_chinese=True):
    map = {}
    for line in lines:
        line = ucd.normalize('NFKC', line)
        separator = ":" if ":" in line else "："
        kv = line.replace(" ", "").replace("\t", "").split(separator)
        if len(kv) != 2:
            continue
        k = kv[0]
        v = kv[1]
        if k == '' or v == '':
            continue
        if filter_chinese and is_chinese(v):
            continue
        map[k] = v
    return map


def project_convert(project):
    if project in ["web", "h5"]:
        return "front-theory"
    if project in ["go"]:
        return "front-goserver"
    return project


def get_pre_dirt(msg_content):
    pre_data_map = get_map(msg_content.split('\n'), False)
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
    projects = list(map(project_convert, branch_map.get('工程模块').split(",")))
    exclude_projects = ["build", "parent", "testapp", "base-common-test"]
    projects = list(filter(lambda name: name not in exclude_projects, projects))
    return branch_map.get('来源分支'), branch_map.get('目标分支'), projects


def get_init_feature_dirt(msg_content):
    init_feature = get_map(msg_content.split('\n'), False)
    require_keys = {"来源分支", "目标分支", "分支负责人"}.difference(init_feature.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    return init_feature


def get_move_branch_dirt(msg_content):
    branch_map = get_map(msg_content.split('\n'))
    require_keys = {"迁移分支", "迁出分支", "迁移模块"}.difference(branch_map.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    return branch_map.get("迁移分支"), branch_map.get("迁出分支"), branch_map.get("迁移模块")


def get_merge_branch_dirt(msg_content):
    branch_map = get_map(msg_content.split('\n'))
    require_keys = {"来源分支", "目标分支", "工程模块", "删除来源"}.difference(branch_map.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    clear_source = branch_map.get('删除来源') == 'true'
    projects = branch_map.get("工程模块", '').strip().split(",")
    return branch_map.get("来源分支"), branch_map.get("目标分支"), projects, clear_source


def get_protect_branch_dirt(msg_content):
    branch_map = get_map(msg_content.split('\n'))
    require_keys = {"目标分支", "工程模块", "是否保护"}.difference(branch_map.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    is_protect = branch_map.get('是否保护') == 'true'
    projects = branch_map.get('工程模块').split(",")
    return branch_map.get("目标分支"), projects, is_protect


def get_build_dirt(msg_content):
    branch_map = get_map(msg_content.split('\n'))
    require_keys = {"目标分支", "立即编译", "构建模块"}.difference(branch_map.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    target_branch = branch_map.get('目标分支')
    target_name = None
    target_date = None
    mapping = get_branch_mapping()
    if re.search(target_regex, target_branch):
        target_date = re.search(target_regex, target_branch).group()
        target_name = target_branch.replace(target_date, "")
    if target_date is None or target_name not in ",".join(mapping.values()):
        raise Exception("目标分支非值班系列【{}】".format(",".join(mapping.values())))
    module = branch_map.get('构建模块')
    if module is None or module not in ["all", "global", "apps"]:
        raise Exception("构建模块输入错误，必须是all,global,apps其中之一")
    is_build = branch_map.get('立即编译') == 'true'
    front_version = branch_map.get("前端预制", '').strip()
    modules = [module]
    if len(front_version) > 0:
        modules.append("front-apps=reimburse:{}".format(front_version))
    protect = "none,{}".format(module)
    return branch_map.get('目标分支'), " ".join(modules), protect, is_build


def send_create_branch_msg(crop, source, target, projects, task_id, version, **user):
    applicant_id = user["applicant"][0]
    applicant_name = user["applicant"][1]
    watchman_id = user["watchman"][0]
    watchman_name = user["watchman"][1]
    project_str = ",".join(projects)
    task_info_list = [{
        "type": 3,
        "keyname": "申请人",
        "value": applicant_name,
        "userid": applicant_id
    }, {
        "keyname": "来源分支",
        "value": source,
    }, {
        "keyname": "目标分支",
        "value": target,
    }, {
        "keyname": "工程模块",
        "value": project_str,
    }]
    msg_content["create_branch_task"]["main_title"]["title"] = "值班助手-来自{}的拉分支请求".format(applicant_name)
    msg_content["create_branch_task"]["horizontal_content_list"] = task_info_list
    msg_content["create_branch_task"]["task_id"] = task_id
    msg_content["create_branch_task"]["button_list"][0]["key"] = "deny@" + task_id
    msg_content["create_branch_task"]["button_list"][1]["key"] = "agree@" + task_id
    # 发送值班人审核通知
    body = crop.send_template_card(watchman_id, msg_content["create_branch_task"])
    # 发送申请人回执消息
    crop.send_text_msg(applicant_id, str(msg_content["create_branch_task_response"].format(watchman_name)))
    # 返回任务消息关键内容
    task_code = body.get("response_code")
    return "{}#{}#{}#{}#{}#{}".format(task_code, applicant_id, source, target,
                                      project_str, version)


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


def build_merge_branch_msg(source, target, project, cluster, task_id):
    task_info_list = [{
        "keyname": "来源分支",
        "value": source,
    }, {
        "keyname": "目标分支",
        "value": target,
    }]
    if project != "build":
        task_info_list.append({
            "keyname": "工程模块",
            "value": project,
        })
    msg_content["merge_branch_task"]["main_title"]["title"] = "值班助手-代码合并任务"
    msg_content["merge_branch_task"]["sub_title_text"] = "{}已发布至{}，请求将代码合并至{}".format(source, cluster, target)
    msg_content["merge_branch_task"]["horizontal_content_list"] = task_info_list
    msg_content["merge_branch_task"]["task_id"] = task_id
    msg_content["merge_branch_task"]["button_list"][0]["key"] = "deny@" + task_id
    msg_content["merge_branch_task"]["button_list"][1]["key"] = "agree@" + task_id
    return msg_content["merge_branch_task"]


def build_move_branch_msg(source, target, group, cluster, task_id):
    task_info_list = [{
        "keyname": "迁移分支",
        "value": source,
    }, {
        "keyname": "迁出分支",
        "value": target,
    }, {
        "keyname": "迁移模块",
        "value": group,
    }]
    msg_content["move_branch_task"]["main_title"]["title"] = "值班助手-分支迁移任务"
    msg_content["move_branch_task"]["sub_title_text"] = "{}已发布至{}，请求将模块迁移至{}".format(source, cluster, target)
    msg_content["move_branch_task"]["horizontal_content_list"] = task_info_list
    msg_content["move_branch_task"]["task_id"] = task_id
    msg_content["move_branch_task"]["button_list"][0]["key"] = "deny@" + task_id
    msg_content["move_branch_task"]["button_list"][1]["key"] = "agree@" + task_id
    return msg_content["move_branch_task"]
