import subprocess
import sys
import time
import os
import json
from pathlib import Path

sys.path.append(r"../../branch-manage")
from dataPre import utils
from dataPre import compareutils

# 加载json配置文件（指定表的关联关系配置）
# tableName: 需要加载的关联表配置的表名
def load_json(tableName):
  fileName = os.path.join(os.curdir, 'json/{}.json'.format(tableName)).replace("\\", "/");
  tables = []
  file = Path(fileName)
  if file.is_file():
    tables = json.loads(file.read_text('utf-8'))
  return tables

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
# rootPath: init-dat工程根路径
# tableNames: 需要恢复的表名集合
def restore_data_pg(connect, rootPath, tableNames):
  cur = connect.cursor()
  for tableName in tableNames:
    tableFile = get_file_path(tableName, rootPath)

    file = Path(tableFile)
    if file.is_file():
      sqls = file.read_text('utf-8')
      if len(sqls.rstrip()) > 0:
        cur.execute(sqls)
  cur.close()
  connect.commit()

#加载数据
# tableName: 加载数据的表名
# connect: 数据库连接
# tableJoins: 和此表关联的表信息
# condition: 附带的查询条件
def load_data(tableName, connect, tableJoins, condition=None, orderBy=None):
  result = {}
  mains = utils.getDataOfPg(tableName, connect, condition, orderBy)
  if len(tableJoins) > 0:
    for item in tableJoins:
      nextTableName = item["tableName"]
      query_field = item["key"]["queryField"]
      value_field = item["key"]["valueField"]
      nextTableJoins = item["tables"]
      nextCondition = item.get("condition", None)
      nextOrderBy = item.get("orderBy", None)

      #获取查询条件的值
      values = []
      for main in mains:
        if main != None:
          values.append(main[value_field]['value'])

      #获取关联查询结果
      if len(values) == 0:
        nextCondition = '1=0'
      else:
        if nextCondition is None or len(nextCondition) == 0:
          nextCondition = '{} in (\'{}\')'.format(query_field, '\',\''.join(values))
        else:
          nextCondition = '({}) and {} in (\'{}\')'.format(nextCondition, query_field,'\',\''.join(values))
      data = load_data(nextTableName, connect, nextTableJoins, nextCondition, nextOrderBy)
      result.update(data)

  result[tableName] = mains
  return result

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
def save_data(newDatas, rootPath):
  for fileName,newData in newDatas.items():
    file = get_file_path(fileName, rootPath)
    with open(file,mode='w+',encoding='utf-8') as file:
      for data in newData:
        sql = compareutils.get_insert(data, fileName)
        file.write(sql)

#获取指定表的预制文件路径
# fileName: 文件名称
# rootPath: init-data工程根路径
def get_file_path(fileName, rootPath):
  index = rootPath.rfind('/')
  if index+1 == len(rootPath):
    rootPath = rootPath[:-1]
  file = Path('{}/src/main/resources/init-data'.format(rootPath))
  if file.exists():
    file = '{}/src/main/resources/init-data/{}.sql'.format(rootPath, fileName)
    return file
  else:
    print("ERROR: 文件夹不存在[{}]!!!!".format(str(file)))
    sys.exit(1)


#提交文件
# tableName: 表名
# rootPath: init-data工程根路径
# commitUser: 提交人
def commit(tableNames, rootPath, commitUser, condition):
  cmd = 'cd ' + rootPath
  for tableName in tableNames:
    cmd += ';git add src/main/resources/init-data/{}.sql'.format(tableName)
  cmd += ';git commit -m "<数据预制>前端多列表方案数据预置--{}(条件：{})"'.format(commitUser, condition)
  # TODO 如果要自动push则需要删除本地分支重新拉取
  # git push -u origin master
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


def pre_multi_list(env, dbName, branch, commitUser, condition):
  # 获取预制环境
  source = env + "." + dbName

  # 预制数据来源环境及租户
  target = "localhost.preset"
  tableName = 'baseapp_query_definition_group'
  tableType = 'multiList'


  #获取数据库配置
  dbConfigs = utils.analysisYaml()
  localConfig = utils.getLocalConfig()

  projectName = 'init-data'
  rootPath = localConfig[projectName]

  utils.chectout_branch(projectName, rootPath, branch)

  #将本地基准库重新创建
  utils.revert_local_db(tableType)

  #获取表关联信息
  tableJoins = load_json(tableName)
  #获取需要操作的所有表
  tableNames = get_all_tables(tableName, tableJoins)
  # print(json.dumps(tableNames))

  # 获取数据库连接信息
  sourceConnect = utils.getPgSql(source, dbConfigs)
  targetConnect = utils.getPgSql(target, dbConfigs)

  #将本地代码的预制数据恢复至本地基准库
  restore_data_pg(targetConnect,rootPath, tableNames)

  #获取预制库中的新数据及本地的旧数据
  newDatas = load_data(tableName, sourceConnect, tableJoins, condition)
  originDatas = load_data(tableName, targetConnect, tableJoins, condition)

  #对比产生差异脚本
  changeLog = compare_and_gen_log(newDatas, originDatas, branch, tableType, source)
  if changeLog is None:
    print("预制租户[{}]与branch[{}]之间无差异".format(source,branch))
    sys.exit(1)
  else:
    #将变更在本地库执行
    file = Path(changeLog)
    if file.is_file():
      sqls = file.read_text('utf-8')
      if len(sqls.rstrip()) > 0:
        cur = targetConnect.cursor()
        cur.execute(sqls)
        cur.close()
        targetConnect.commit()
    else:
      print("ERROR: 未找到变更记录文件！！！")
      sys.exit(1)


  #有差异时，将本地升级之后的数据生成预制脚本
  save_data(load_data(tableName, targetConnect, tableJoins), rootPath)

  #编译
  # cmd = 'cd ' + rootPath + ';mvn clean install'
  # [result, msg] = subprocess.getstatusoutput(cmd)
  # if result != 0:
  #   print("编译报错！！！")
  #   print("[{}]{}".format(result, msg))
  #   sys.exit(1)

  #自动提交
  if commitUser != None and len(commitUser.lstrip())>0:
    commit(tableNames, rootPath, commitUser, condition)
    print("自动提交")
  # 记录操作日志
  operation_log(source, branch, condition, commitUser, changeLog, tableType)


  print("本次预制多列表方案操作为：")
  print("预制租户: " + source)
  print("分支: " + branch)
  print("查询条件: " + condition)
  print("提交人: " + commitUser)
