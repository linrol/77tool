data_pre_new_help = ">**新列表方案** " \
                    "\n>环　境：<font color=\"comment\">输入预制数据来源环境，例：temp1</font>" \
                    "\n>租　户：<font color=\"comment\">输入预制数据来源租户，例：47L0LP505840001</font>" \
                    "\n>分　支：<font color=\"comment\">输入预制的代码分支，例：feature-purchase-budget</font>" \
                    "\n>列表组：<font color=\"comment\">输入列表方案组名称，例：Budget_Plan_Change_list</font>" \
                    "\n>合并人：<font color=\"comment\">输入分支有权限合并者人姓名（空时无需MR，直接提交）</font>" \
                    "\n>" \
                    "\n>复制以上模版，修改后发给我，成功预制后将以消息通知到你" \
                    "\n>或点击[去小程序操作](https://work.weixin.qq.com)"

data_pre_old_help = ">**老列表方案** " \
                    "\n>环　境：<font color=\"comment\">输入预制数据来源环境，例：temp1</font>" \
                    "\n>租　户：<font color=\"comment\">输入预制数据来源租户，例：47L0LP505840001</font>" \
                    "\n>分　支：<font color=\"comment\">输入预制的代码分支，例：feature-purchase-budget</font>" \
                    "\n>列表组：<font color=\"comment\">输入列表方案组名称，例：Budget_Plan_Change_list</font>" \
                    "\n>合并人：<font color=\"comment\">输入分支有权限合并者人姓名（空时无需MR，直接提交）</font>" \
                    "\n>" \
                    "\n>复制以上模版，修改后发给我，成功预制后将以消息通知到你" \
                    "\n>或点击[去小程序操作](https://work.weixin.qq.com)"

msg_params = {
  "touser": "",
  "msgtype": "",
  "agentid": ""
}

from xml.etree.ElementTree import fromstring
import unicodedata as ucd

def xml2map(raw_xml):
    data = {}
    for node in list(fromstring(raw_xml.decode('utf-8'))):
        data[node.tag] = node.text
    return data

def is_chinese(word):
    for ch in word:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False

def get_pre_map(lines):
    pre_map = {}
    for line in lines:
        line = ucd.normalize('NFKC', line)
        separator = ":" if ":" in line else "："
        kv = line.replace(" ", "").split(separator)
        if len(kv) != 2:
            continue
        k = kv[0]
        v = kv[1]
        if k == '' or v == '' or is_chinese(v):
            continue
        pre_map[k] = v
    require_keys = {"环境","租户","分支","列表组"}.difference(pre_map.keys())
    if len(require_keys) > 0:
        raise Exception("请检查【{}】的输入参数合法性".format("，".join(list(require_keys))))
    tenant_id = "tenant" + pre_map.get('租户')
    return pre_map.get('环境'), tenant_id, pre_map.get('分支'), "branch.bot", pre_map.get('列表组')