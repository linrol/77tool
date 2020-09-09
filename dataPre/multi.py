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

#恢复预制文件的预制数据到指定的数据库---pg
# connect: pg数据库连接
# path: init-dat工程脚本存放路径
def restore_data_pg(connect, path):
  cur = connect.cursor()
  tableFiles = get_all_files('{}/multiList'.format(path), "MultiList_")
  for tableFile in tableFiles:
    file = Path(tableFile)
    if file.is_file():
      sqls = file.read_text('utf-8')
      if len(sqls.rstrip()) > 0:
        cur.execute(sqls)
  cur.close()
  connect.commit()
  return tableFiles

#加载数据(返回数据按照表进行分割)
# tableName: 加载数据的表名
# connect: 数据库连接
# tableJoins: 和此表关联的表信息
# condition: 附带的查询条件
def load_data(tableName, connect, tableJoins, condition=None, orderBy=None):
  result = {}
  mains = utils.getDataOfPg(tableName, connect, condition, orderBy)
  result[tableName] = mains
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

  return result


#加载数据(返回数据按照分组进行分割)
# tableName: 加载数据的表名
# connect: 数据库连接
# tableJoins: 和此表关联的表信息
# groupField: 分组字段
# condition: 附带的查询条件
def load_data_of_group(tableName, connect, tableJoins, groupField, condition=None, orderBy=None):
  result = {}
  mains = utils.getDataOfPg(tableName, connect, condition, orderBy)

  for main in mains:
    if main != None:
      groupValue = main[groupField]['value']
      id = main['id']['value']
      #获取关联查询结果
      condition = 'id = \'{}\''.format(id)
      data = load_data(tableName, connect, tableJoins, condition)
      result[groupValue] = data
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
# scriptPath: init-data工程脚本存放路径
def save_data(newDatas, scriptPath):
  files = []
  filePath = '{}/multiList/'.format(scriptPath)
  if not os.path.exists(filePath):
    os.makedirs(filePath, 0o777)
  for groupName,newData in newDatas.items():
    file = os.path.join(filePath, 'MultiList_{}.sql'.format(groupName))
    files.append(file)
    with open(file,mode='w+',encoding='utf-8') as file:
      for tableName,datas in newData.items():
        file.write('--{}\n'.format(tableName))
        for data in datas:
          sql = compareutils.get_insert(data, tableName)
          file.write(sql)
        file.write('\n')
  return files


#获取指定路径下，指定前缀的文件路径集合
# rootPath: init-data工程脚本存放路径
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


#提交文件
# tableName: 表名
# rootPath: init-data工程根路径
# commitUser: 提交人
def commit(rootPath, commitUser, condition):
  cmd = 'cd ' + rootPath
  cmd += ';git add src/main/resources/init-data/multiList/MultiList_*'
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
  scriptPath = localConfig[tableType][projectName]

  utils.chectout_branch(projectName, rootPath, branch)

  #将本地基准库重新创建
  utils.revert_local_db(tableType)

  #获取表关联信息
  tableJoins = load_json(tableName)

  # 获取数据库连接信息
  sourceConnect = utils.getPgSql(source, dbConfigs)
  targetConnect = utils.getPgSql(target, dbConfigs)

  #将本地代码的预制数据恢复至本地基准库
  oldFiles = restore_data_pg(targetConnect, scriptPath)

  #获取预制库中的新数据及本地的旧数据
  newDatas = load_data(tableName, sourceConnect, tableJoins, condition)
  originDatas = load_data(tableName, targetConnect, tableJoins, condition)

  #对比产生差异脚本
  changeLog = compare_and_gen_log(newDatas, originDatas, branch, tableType, source)
  if changeLog is None:
    sourceConnect.close()
    targetConnect.close()
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


  #有差异时，先将本地脚本移除，然后将本地升级之后的数据生成预制脚本
  for oldFile in oldFiles:
    os.remove(oldFile)
  filePaths = save_data(load_data_of_group(tableName, targetConnect, tableJoins, 'name'),scriptPath)

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
    commit(rootPath, commitUser, condition)
    print("自动提交")
  # 记录操作日志
  operation_log(source, branch, condition, commitUser, changeLog, tableType)


  print("本次预制多列表方案操作为：")
  print("预制租户: " + source)
  print("分支: " + branch)




if __name__ == "__main__":
  pre_multi_list('localhost', 'testapp', 'ztb-test', 'aa', None)