import sys
from pathlib import Path

sys.path.append(r"../../branch-manage")
#
from dataPre import compareutils
from dataPre import utils

def save_data(datas, idMap, preTypeConfig):
  for projectName,ids in idMap.items():
    newDatas = []
    with open(preTypeConfig[projectName],mode='r',encoding='utf-8') as file:
      sqls = file.readlines()
      for sql in sqls:
        if sql.startswith('UPDATE '):
          break
        else:
          newDatas.append(sql)

    for data in datas:
      id = data['id']['value']
      if id in ids:
        if data['layout_template_id']['value'] == None:
          layoutId = 'NULL'
        else:
          layoutId ='\'{}\''.format(data['layout_template_id']['value'])

        if data['mobile_template_id']['value'] == None:
          mobileId = 'NULL'
        else:
          mobileId='\'{}\''.format(data['mobile_template_id']['value'])

        if data['print_template_id']['value'] == None:
          printId = 'NULL'
        else:
          printId='\'{}\''.format(data['print_template_id']['value'])

        sql = 'UPDATE baseapp_bill_type SET "layout_template_id" = {}, "mobile_template_id" = {}, "print_template_id" = {} WHERE "id" = \'{}\';\n'.format(layoutId, mobileId, printId, id)
        newDatas.append(sql)

    newDatas.append("--启用当前会话所有触发器\n")
    newDatas.append("SET session_replication_role = DEFAULT;\n")

    with open(preTypeConfig[projectName],mode='w+',encoding='utf-8') as file:
      for sql in newDatas:
        file.write(sql)

def compare(sourceConnect, targetConnect, idMap):
  allIds = []
  for projectName,ids in idMap.items():
    allIds.extend(ids)

  condition = 'id in (\'{}\')'.format('\',\''.join(allIds))

  newBillTypes = utils.getDataOfPg('baseapp_bill_type', sourceConnect, condition)
  newBillTypeMap = compareutils.list_to_map(newBillTypes)
  oldBillTypeMap = compareutils.list_to_map(utils.getDataOfPg('baseapp_bill_type', targetConnect, condition))

  changeCount = 0
  for id,new in newBillTypeMap.items():
    old = oldBillTypeMap.get(id, {})
    hasChange = False
    if new['layout_template_id'].get('value', '') != old['layout_template_id'].get('value', '') :
      print("单据类型【{}】单据模板旧值【{}】,新值【{}】".format(new['name']['value'], old['layout_template_id'].get('value', '空'), new['layout_template_id'].get('value', '空')))
      hasChange = True
    if new['mobile_template_id'].get('value', '') != old['mobile_template_id'].get('value', '') :
      print("单据类型【{}】手机模板旧值【{}】,新值【{}】".format(new['name']['value'], old['mobile_template_id'].get('value', '空'), new['mobile_template_id'].get('value', '空')))
      hasChange = True
    if new['print_template_id'].get('value', '') != old['print_template_id'].get('value', '') :
      print("单据类型【{}】打印模板旧值【{}】,新值【{}】".format(new['name']['value'], old['print_template_id'].get('value', '空'), new['print_template_id'].get('value', '空')))
      hasChange = True
    if hasChange:
      changeCount = changeCount + 1
  if changeCount > 0:
    print("BillType：{}条".format(changeCount))
    return newBillTypes
  else:
    print("BillType没有变动！")
    return None


#恢复预制文件的预制数据到指定的数据库并返回预制数据id---pg
# connect: pg数据库连接
# filePath: billType文件路径
def restore_data_pg(connect, filePath):
  cur = connect.cursor()

  file = Path(filePath)
  if file.is_file():
    sqls = file.read_text('utf-8')
    if len(sqls.rstrip()) > 0:
      cur.execute(sqls)
  else:
    print("ERROR: BillType文件错误({})".format(filePath))
    sys.exit(1)
  cur.close()
  connect.commit()


# 获取本工程相关的单据类型id
# connect: pg数据库连接
# filePath: billType文件路径
def get_ids(connect, excludeids):
  cur = connect.cursor()

  if excludeids is None or len(excludeids) == 0:
    sql = "select id from baseapp_bill_type";
  else:
    sql = "select id from baseapp_bill_type where id not in (\'{}\')".format('\',\''.join(excludeids));
  cur.execute(sql)
  datas = cur.fetchall()
  ids = []
  for data in datas:
    ids.append(data[0])
  cur.close()
  return ids


def pre_bill_type(env, dbName, branch, commitUser):
  source = env + "." + dbName

  target = "localhost.preset"
  preType= 'billType'

  localConfig = utils.getLocalConfig()
  dbConfigs = utils.analysisYaml()

  preTypeConfig = localConfig.get(preType, None)
  if preTypeConfig is None:
    print("ERROR: 模板id配置信息为空！！！")
    sys.exit(1)

  #将本地基准库重新创建
  utils.revert_local_db(preType)

  sourceConnect = utils.getPgSql(source, dbConfigs)
  targetConnect = utils.getPgSql(target, dbConfigs)
  #检出最新代码并恢复到数据库
  idMap = {}
  excludeIds = []
  for projectName,dataPath in preTypeConfig.items():
    utils.chectout_branch(projectName, localConfig[projectName], branch)
    #将本地代码的预制数据恢复至本地基准库
    restore_data_pg(targetConnect,dataPath)
    ids = get_ids(targetConnect, excludeIds)
    idMap[projectName] = ids
    excludeIds.extend(ids)


  #对比产生差异
  # fileName = compare.compare_and_genSql(source, target)
  datas = compare(sourceConnect, targetConnect, idMap)

  sourceConnect.close()
  targetConnect.close()

  if datas == None:
    print("source[{}]与分支[{}]之间无差异".format(source,branch))
    sys.exit(1)

  #保存数据
  save_data(datas, idMap, preTypeConfig)

  print("本次操作为：")
  print(source)
  print(target)
  print(branch)
  print(commitUser)

