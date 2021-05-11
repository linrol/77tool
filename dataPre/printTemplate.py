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
  tableFiles = utils.get_all_files('{}/billTypeTemplate'.format(path), "BillTypeTemplate_")
  return utils.execute_sql_pg(connect, tableFiles)

#对比新旧数据，产生升级脚本存放到指定分支目录下
# newDatas: 新数据（即：从预制租户取到的数据）
# originDatas: 旧数据（即：从指定分支代码库取到的预制数据）
# branch: 分支（指定分支）
def compare_and_gen_log(sourceTemplateInfo, originTemplateInfo, branch, tableType, source):
  changeDatas = compareutils.compare_and_genSql('baseapp_bill_type_template', sourceTemplateInfo.getColumnMap(), sourceTemplateInfo.getDatas(), originTemplateInfo.getDatas())

  if changeDatas is not None and len(changeDatas) > 0:
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
def save_data(targetConnect, dataPath, columnMap):
  templates = utils.getDataOfPg("baseapp_bill_type_template", targetConnect)
  save_bill_type_template(templates,dataPath, columnMap)

#保存BillTypeTemplate数据
def save_bill_type_template(tableDataInfo, dataPath, columns):
  billTypeTemps = {}
  for data in tableDataInfo.getDatas():
    objectType = data['object_type']
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
        sql = compareutils.get_insert(billTypeTemp, 'baseapp_bill_type_template', columns)
        file.write(sql)


#提交文件
# dataPath: init-data工程根路径
# commitUser: 提交人
def commit(rootPath, commitUser):
  cmd = 'cd ' + rootPath
  cmd += ';git add src/main/resources/init-data/uiConfig'
  cmd += ';git add src/main/resources/init-data/billTypeTemplate'
  cmd += ';git commit -m "<数据预制>前端UiConfig数据预置--{}"'.format(commitUser)
  [result, msg] = subprocess.getstatusoutput(cmd)
  if result != 0:
    print("ERROR: 提交报错！！！")
    print("[{}]{}".format(result, msg))
    sys.exit(1)


def pre_print_template(env, dbName, branch, templateIds, commitUser=None):
  # 获取预制环境
  source = env + "." + dbName

  # 预制数据来源环境及租户
  target = "localhost.preset"
  tableType = 'form'

  dbConfigs = utils.analysisYaml()
  localConfig = utils.getLocalConfig()

  projectName = 'init-data'
  rootPath = localConfig[projectName]
  dataPath = rootPath + '/src/main/resources/init-data'

  utils.chectout_branch(projectName, rootPath, branch)

  #将本地基准库重新创建
  utils.revert_local_db(tableType)

  # 获取数据库连接信息
  sourceConnect = utils.getPgSql(source, dbConfigs)

  targetConnect = utils.getPgSql(target, dbConfigs)
  #将本地代码的预制数据恢复至本地基准库
  oldFiles = restore_data_pg(targetConnect,dataPath)

  #获取预制库中的新数据及本地的旧数据
  templateCondition = 'id in (\'{}\')'.format('\',\''.join(templateIds))
  sourceTemplateInfo = utils.getDataOfPg("baseapp_bill_type_template", sourceConnect,templateCondition)
  originTemplateInfo = utils.getDataOfPg("baseapp_bill_type_template", targetConnect,templateCondition)


  if len(sourceTemplateInfo.getDatas()) == 0 and len(originTemplateInfo.getDatas()) == 0:
    print("ERROR: BillTypeTemplate不存在（{}）！！！".format(templateCondition))
    sys.exit(1)

  #对比产生差异脚本
  changeLog = compare_and_gen_log(sourceTemplateInfo, originTemplateInfo, branch, tableType, source)
  if changeLog is None:
    sourceConnect.close()
    targetConnect.close()
    print("预制租户[{}]与branch[{}]之间无差异".format(source,branch))
    sys.exit(1)
  else:
    #将变更在本地库执行
    utils.execute_sql_pg(targetConnect, [changeLog])

  #有差异时，先将本地脚本移除，然后将本地升级之后的数据生成预制脚本
  for oldFile in oldFiles:
    os.remove(oldFile)
  #有差异时，将本地升级之后的数据生成预制脚本
  save_data(targetConnect, dataPath, sourceTemplateInfo.getColumnMap())

  sourceConnect.close()
  targetConnect.close()

  #自动提交
  if commitUser != None and len(commitUser.lstrip())>0:
    commit(rootPath, commitUser)
    print("自动提交")
  # 记录操作日志
  utils.operation_log(source, branch, None, commitUser, changeLog, tableType)


  print("本次预制打印模板操作为：")
  print("预制租户: " + source)
  print("分支: " + branch)
  print("提交人: " + commitUser)


#表单或老列表方案预置
#python3 printTemplate.py release PSE5KP504EN000F release 张三 j2af83PZR
if __name__ == "__main__":
  if len(sys.argv) < 6 :
    print ("ERROR: 输入参数错误, 正确的参数为：<source ENV> <tenantId> <branch> <commitUser> [<printTemplateId>...]")
    sys.exit(1)

  env = sys.argv[1]
  dbName = 'tenant' + sys.argv[2]
  branch = sys.argv[3]
  commitUser = sys.argv[4]
  uiConfigIds = sys.argv[5:]

  pre_print_template(env, dbName, branch, uiConfigIds, commitUser)
