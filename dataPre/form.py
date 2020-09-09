import subprocess
import sys
import time
import os
import json
from pathlib import Path

sys.path.append(r"../../branch-manage")
from dataPre import utils
from dataPre import compareutils

#根据指定表和此表与其他表的关联关系，获取所有表名（包含此表本身和关联的表）
# tableName: 指定表
# tableJoins: 指定表的关联关系
def get_all_tables(tableName, tableJoins):
  tableNames = [tableName]
  if tableJoins is not None:
    for item in tableJoins:
      nextTableName = item["tableName"]
      nextTableJoins = item["tables"]
      tableNames.extend(get_all_tables(nextTableName, nextTableJoins))
  return tableNames

#恢复预制文件的预制数据到指定的数据库---pg
# connect: pg数据库连接
# dataPath: 数据存储根路径路径
# tableNames: 需要恢复的表名集合
def restore_data_pg(connect, path):
  cur = connect.cursor()
  tableFiles = get_all_files('{}/uiConfig'.format(path), "UiConfig_")
  tableFiles.extend(get_all_files('{}/billTypeTemplate'.format(path), "BillTypeTemplate_"))

  for tableFile in tableFiles:
    file = Path(tableFile)
    if file.is_file():
      sqls = file.read_text('utf-8')
      if len(sqls.rstrip()) > 0:
        cur.execute(sqls)
  cur.close()
  connect.commit()
  return tableFiles

#获取指定路径下，指定前缀的文件路径集合
# rootPath: 要检查的路径
# pre: 要获取的文件名前缀
def get_all_files(rootPath, pre=None):
  index = rootPath.rfind('/')
  if index+1 == len(rootPath):
    rootPath = rootPath[:-1]

  filePaths = []
  if not os.path.exists(rootPath):
    return filePaths

  listdir = os.listdir(rootPath)
  for fileName in listdir:
    filePath = '{}/{}'.format(rootPath, fileName)
    if os.path.isdir(filePath):
      child = get_all_files(filePath, pre)
      if child is not None and len(child) > 0:
        filePaths.extend(child)
    elif pre is None or fileName.startswith(pre):
      filePaths.append(filePath)
  return filePaths

#加载数据
# tableName: 加载数据的表名
# connect: 数据库连接
def load_data(tableNames, connect):
  result = {}
  for tableName,condition in tableNames.items():
    datas = utils.getDataOfPg(tableName, connect, condition)
    result[tableName] = datas
  return result;

#对比新旧数据，产生升级脚本存放到指定分支目录下
# newDatas: 新数据（即：从预制租户取到的数据）
# originDatas: 旧数据（即：从指定分支代码库取到的预制数据）
# branch: 分支（指定分支）
def compare_and_gen_log(newDatas, originDatas, branch, tableType, source):
  changeDatas = []
  for name,newData in newDatas.items():
    result = compareutils.compare_and_genSql(name, newData, originDatas.get(name))
    if result is None or len(result) == 0:
      continue
    else:
      changeDatas.extend(result)

  if len(changeDatas) > 0:
    filePath = "./log/{}/{}/".format(tableType, branch)
    fileName = "{}_to_{}-{}.sql".format(source,branch, time.strftime("%Y%m%d%H%M%S",time.localtime()))
    if not os.path.exists(filePath):
      os.makedirs(filePath, 0o777)
    filePath = os.path.join(filePath, fileName)
    with open(filePath,mode='a+',encoding='utf-8') as file:
      for changeData in changeDatas:
        file.writelines(changeData)
      file.flush()
      return os.path.abspath(filePath)


#保存预制数据到相应的预制文件
# newDatas: 新数据（本地升级之后的数据）
# rootPath: init-data工程根路径
def save_data(newDatas, dataPath):
  for tableName,newData in newDatas.items():
    if(tableName == 'baseapp_ui_config'):
      save_ui_config(newData,dataPath)
    elif tableName == 'baseapp_bill_type_template':
      save_bill_type_template(newData,dataPath)
    else:
      print("ERROR: 表【{}】未处理!!!".format(tableName))

#保存UiConfig数据
def save_ui_config(newData, dataPath):
  uiConfigs = {}
  for data in newData:
    uiType = data['type']['value']
    if uiType is None or uiType.lstrip()=='':
      uiType = 'null'

    content = data['content']['value']
    if type(content) is int:
      entityName = 'Int'
    elif type(content) is float:
      entityName = 'Float'
    elif type(content) is bool:
      entityName = 'Boolean'
    elif type(content) is str:
      entityName = 'String'
    elif type(content) is list or type(content) is tuple:
      entityName = 'List'
    elif type(content) is dict:
      entityName = content.get('entityName', 'None')
    else:
      print("ERROR: content字段类型[{}]未知!!!".format(type(content)))
      sys.exit(1)

    strName = '{}_{}'.format(uiType, entityName)
    uiDatas = uiConfigs.get(strName, [])
    uiDatas.append(data)
    uiConfigs[strName] =uiDatas
  filePath = '{}/uiConfig/'.format(dataPath)
  if not os.path.exists(filePath):
    os.makedirs(filePath, 0o777)
  for key,lists in uiConfigs.items():
    file = os.path.join(filePath, 'UiConfig_{}.sql'.format(key))
    with open(file,mode='w+',encoding='utf-8') as file:
      for uiData in lists:
        sql = compareutils.get_insert(uiData, 'baseapp_ui_config')
        file.write(sql)

#保存BillTypeTemplate数据
def save_bill_type_template(newData, dataPath):
  billTypeTemps = {}
  for data in newData:
    objectType = data['object_type']['value']
    if objectType is None or objectType.lstrip()=='':
      objectType = 'null'
    billTypeTempDatas = billTypeTemps.get(objectType, [])
    billTypeTempDatas.append(data)
    billTypeTemps[objectType] = billTypeTempDatas
  filePath = '{}/billTypeTemplate/'.format(dataPath)
  if not os.path.exists(filePath):
    os.makedirs(filePath, 0o777)
  for key,lists in billTypeTemps.items():
    file = os.path.join(filePath, 'BillTypeTemplate_{}.sql'.format(key))
    with open(file,mode='w+',encoding='utf-8') as file:
      for billTypeTemp in lists:
        sql = compareutils.get_insert(billTypeTemp, 'baseapp_bill_type_template')
        file.write(sql)


#提交文件
# dataPath: init-data工程根路径
# commitUser: 提交人
def commit(rootPath, commitUser):
  cmd = 'cd ' + rootPath
  cmd += ';git add src/main/resources/init-data/uiConfig/UiConfig_*'
  cmd += ';git add src/main/resources/init-data/billTypeTemplate/BillTypeTemplate_*'
  cmd += ';git commit -m "<数据预制>前端UiConfig数据预置--{}"'.format(commitUser)
  [result, msg] = subprocess.getstatusoutput(cmd)
  if result != 0:
    print("ERROR: 提交报错！！！")
    print("[{}]{}".format(result, msg))
    sys.exit(1)

# 记录操作日志
# source: 预制租户信息
# branch: 分支
# condition: 查询条件
# commitUser: 提交人
# fileName: 升级脚本文件名
def operation_log(source, branch, condition, commitUser, fileName, tableType):
  logFile = "./log/operation-{}.log".format(tableType)
  file = Path(logFile)
  log = ''
  if file.is_file():
    log = file.read_text("utf-8")

  with open(logFile, mode='w+', encoding='utf-8') as file:
    file.writelines('预制租户【{}】预制分支【{}】提交人【{}】查询条件【{}】 升级文件【{}】\n{}'.format(source, branch, commitUser, condition, fileName, log))



# 检查前端表单预制数据版本是否匹配
def check_version(sourceConnect):
  uiConfigs = utils.getDataOfPg("baseapp_ui_config", sourceConnect, 'content->>\'templates\' <>\'null\' and content->>\'templates\' <>\'[]\'')
  templates = utils.getDataOfPg("baseapp_bill_type_template", sourceConnect)
  templateVersions = parse_template_version(templates)
  uiConfigVersions = parse_uiConfig_version(uiConfigs)

  noUi = []
  noUiVersion = []
  isPass = True
  for id,version in templateVersions.items():
    uiConfigContent = uiConfigVersions.get(id, None)
    if uiConfigContent == None :
      noUi.append(id)
      continue
    uiConfigVersion = uiConfigContent.get('version',None)
    if uiConfigVersion is None:
      noUiVersion.append(uiConfigContent['id'])
      uiConfigVersion = '1.0.0'
    if(version != uiConfigVersion):
      entityName = uiConfigContent['entityName']
      uiConfigId = uiConfigContent['id']
      print("ERROR:entityName[{}]:template[{}][{}] 和 UiConfig[{}][{}]版本不一致!!!".format(entityName, id, version, uiConfigId, uiConfigVersion))
      isPass = False

  return isPass

# 解析模板版本
def parse_template_version(templates):
  templateVersions = {}
  noVersion = []
  for template in templates:
    content = template['content']['value']
    version = content.get('version', None)
    if version is None:
      noVersion.append(template['id']['value'])
      version = '1.0.0'
    templateVersions[template['id']['value']] = version

  return templateVersions

# 解析uiConfig对应的模板id
def parse_uiConfig_version(uiConfigs):
  uiConfigVersions = {}
  for uiConfig in uiConfigs:
    content = uiConfig['content']['value']
    version = content['version']
    templates = content['templates']
    for template in templates:
      uiConfigVersions[template['id']] = content
  return uiConfigVersions




def pre_form(env, dbName, branch, commitUser):
  # 获取预制环境
  source = env + "." + dbName

  # 预制数据来源环境及租户
  target = "localhost.preset"
  tableType = 'form'
  #获取需要操作的所有表及其查询条件
  tableNames = {'baseapp_ui_config':'type not in (\'notifyShow\',\'shortCuts\',\'portletLayout\')','baseapp_bill_type_template':''}

  dbConfigs = utils.analysisYaml()
  localConfig = utils.getLocalConfig()

  projectName = 'init-data'
  rootPath = localConfig[projectName]
  dataPath = localConfig[tableType][projectName]

  utils.chectout_branch(projectName, rootPath, branch)

  #将本地基准库重新创建
  utils.revert_local_db(tableType)

  # 获取数据库连接信息
  sourceConnect = utils.getPgSql(source, dbConfigs)

  #检查UiConfig和Template的版本是否匹配
  if not check_version(sourceConnect):
    print("ERROR: 检查UiConfig和Template的版本不通过！！！")
    sys.exit(1)
  else:
    print('版本检查通过')

  targetConnect = utils.getPgSql(target, dbConfigs)

  #将本地代码的预制数据恢复至本地基准库
  oldFiles = restore_data_pg(targetConnect,dataPath)

  #获取预制库中的新数据及本地的旧数据
  newDatas = load_data(tableNames, sourceConnect)
  originDatas = load_data(tableNames, targetConnect)

  #对比产生差异脚本
  changeLog = compare_and_gen_log(newDatas, originDatas, branch, tableType, source)
  if changeLog is None:
    sourceConnect.close()
    targetConnect.close()
    print("预制租户[{}]与branch[{}]之间无差异".format(source,branch))
    sys.exit(1)

  #有差异时，先将本地脚本移除，然后将本地升级之后的数据生成预制脚本
  for oldFile in oldFiles:
    os.remove(oldFile)
  #有差异时，将本地升级之后的数据生成预制脚本
  save_data(load_data(tableNames, sourceConnect), dataPath)

  sourceConnect.close()
  targetConnect.close()

  #编译
  # cmd = 'cd ' + rootPath + ';mvn clean install'
  # [result, msg] = subprocess.getstatusoutput(cmd)
  # if result != 0:
  #   print("编译报错！！！")
  #   print("[{}]{}".format(result, msg))
  #   sys.exit(1)

  #自动提交
  if commitUser != None and len(commitUser.lstrip())>0:
    commit(rootPath, commitUser)
    print("自动提交")
  # 记录操作日志
  operation_log(source, branch, None, commitUser, changeLog, tableType)


  print("本次预制表单操作为：")
  print("预制租户: " + source)
  print("分支: " + branch)
  print("提交人: " + commitUser)

# if __name__ == "__main__":
#   # 获取预制环境
#   env = 'reports'
#   dbName='tenantLNCEPQ50QX80001'
#   branch ='ztb-test'
#
#   # dbConfigs = utils.analysisYaml()
#   # pgConfig = dbConfigs.get(env,None)
#   # branch = 'dev'
#   # tenantId = pgConfig.get('tenantId', None)
#
#   commitUser = ''
#   pre_form(env, dbName, branch, commitUser)
