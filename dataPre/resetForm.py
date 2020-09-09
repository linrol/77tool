import subprocess
import sys
import time
import os
import json
from pathlib import Path

sys.path.append(r"../../branch-manage")
from dataPre import utils
from dataPre import compareutils


#恢复预制文件的预制数据到指定的数据库---pg
# connect: pg数据库连接
# dataPath: 数据存储根路径路径
def restore_data_pg(connect, path):
  cur = connect.cursor()
  tableFiles = get_all_files('{}/uiConfig'.format(path), "UiConfig_")
  tableFiles.extend(get_all_files('{}/billTypeTemplate'.format(path), "BillTypeTemplate_"))
  cur.execute('DELETE FROM baseapp_ui_config;')
  cur.execute('DELETE FROM baseapp_bill_type_template;')

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

#备份预制数据到文件
def reset_data(newDatas, env, dbName, branch):
  filePath = "./log/reset/"
  fileName = "{}_to_{}_{}-{}.sql".format(branch, env,dbName, time.strftime("%Y%m%d%H%M%S",time.localtime()))
  if not os.path.exists(filePath):
    os.makedirs(filePath, 0o777)
  filePath = os.path.join(filePath, fileName)
  with open(filePath,mode='a+',encoding='utf-8') as file:
    for tableName,newData in newDatas.items():
      for data in newData:
        sql = compareutils.get_insert(data, tableName)
        file.write(sql)
  return filePath

# 记录操作日志
# source: 预制租户信息
# branch: 分支
# fileName: 升级脚本文件名
def operation_log(source, branch, fileName, tableType):
  logFile = "./log/operation-{}.log".format(tableType)
  file = Path(logFile)
  log = ''
  if file.is_file():
    log = file.read_text("utf-8")

  with open(logFile, mode='w+', encoding='utf-8') as file:
    file.writelines('重置租户【{}】数据来源分支【{} 备份文件【{}】\n{}'.format(source, branch, fileName, log))


def reset_form(env, dbName, branch):
  # 获取重置环境
  source = env + "." + dbName

  #获取需要操作的所有表及其查询条件
  tableType = 'reset'
  tableNames = {'baseapp_ui_config':'','baseapp_bill_type_template':''}

  dbConfigs = utils.analysisYaml()
  localConfig = utils.getLocalConfig()

  projectName = 'init-data'
  rootPath = localConfig[projectName]
  dataPath = localConfig[tableType][projectName]

  #检出指定分支
  utils.chectout_branch(projectName, rootPath, branch)

  # 获取数据库连接信息
  sourceConnect = utils.getPgSql(source, dbConfigs)

  #获取预制租户的数据
  newDatas = load_data(tableNames, sourceConnect)

  #备份预制租户数据
  resetFile = reset_data(newDatas, env, dbName, branch)

  #将本地代码的预制数据恢复至本地基准库
  restore_data_pg(sourceConnect,dataPath)

  sourceConnect.close()

  # 记录操作日志
  operation_log(source, branch, resetFile, tableType)


  print("本次表单数据重置操作为：")
  print("重置租户: " + source)
  print("分支: " + branch)


if __name__ == "__main__":
  # 获取预制环境
  env = 'localhost'
  dbName='testapp'
  branch ='ztb-test'

  # dbConfigs = utils.analysisYaml()
  # pgConfig = dbConfigs.get(env,None)
  # branch = 'dev'
  # tenantId = pgConfig.get('tenantId', None)

  reset_form(env, dbName, branch)
