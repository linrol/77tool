import json
import subprocess
import sys
import psycopg2
import os
import yaml
import gitlab
from pathlib import Path

URL='http://gitlab.q7link.com'
TOKEN='khw5vE4nW48kibsY-CgM'


# jsonFields = ['content']
# booleanFields = ['is_disabled','is_system','is_default','is_print','is_mobile','is_display','is_total','is_virtual','is_extend']
isSystemTable = ['baseapp_bill_type_template', 'baseapp_list_column', 'baseapp_list_column_schema', 'baseapp_list_columns_definition', 'baseapp_list_columns_schema', 'baseapp_list_columns_schema_context_field', 'baseapp_list_columns_schema_sort_field', 'baseapp_query_list_definition', 'baseapp_query_item', 'baseapp_query_item_schema', 'baseapp_query_definition', 'baseapp_query_schema', 'baseapp_query_definition_group','baseapp_list_column_group','baseapp_menu_func','baseapp_menu','baseapp_report_definition']

class ColumnInfo():
  excludeFields = ['entry_src_system_id', 'external_system_code', 'external_object_type', 'external_object_id', 'created_user_id', 'created_time', 'modified_user_id', 'modified_time', 'is_init_data', 'is_deleted', 'last_request_id', 'last_modified_user_id', 'last_modified_time', 'customized_fields','data_version']
  def __init__(self, name, type, index):
    self.__name = name
    self.__type = type
    self.__index = index

  def getName(self):
    return self.__name
  def getType(self):
    return self.__type
  def getIndex(self):
    return self.__index
  def getIsExclude(self):
    return (self.__name in ColumnInfo.excludeFields)

class TableDataInfo():
  __tableName = None
  __exists = True
  __sql = None
  __datas = []
  __dataMap = {}
  __columnMap = {}

  def __init__(self, tableName, columnDescription, datas, sql, exists=True):
    self.__tableName = tableName
    self.__exists = exists
    if not exists:
      return

    self.__sql = sql
    # 表字段解析
    columnMap={}
    for index,field in enumerate(columnDescription):
      field_name = field.name
      field_type = field.type_code
      columnInfo = ColumnInfo(field_name, field_type, index)
      columnMap[field_name] = columnInfo
    self.__columnMap = columnMap

    # 表数据解析
    results=[]
    resultMap={}
    for data in datas:
      result = {}
      for name,columnInfo in columnMap.items():
        if not columnInfo.getIsExclude():
          field_name = columnInfo.getName()
          field_type = columnInfo.getType()
          field_index = columnInfo.getIndex()
          if field_type == 3802:
            #防止JSON中的中文转义，此处先转为字符串在转为JSON
            if data[field_index] != None:
              result[field_name] = json.loads(json.dumps(data[field_index]))
            else:
              result[field_name] = None
          elif field_name == 'is_system':
            #部分表的is_system字段需要默认设置为True
            if tableName in isSystemTable:
              result[field_name] = True
            else:
              result[field_name] = data[field_index]
          else:
            result[field_name] = data[field_index]
      results.append(result)
      resultMap[result['id']] = result
    self.__datas = results
    self.__dataMap = resultMap

  def getTableName(self):
    return self.__tableName
  def getSql(self):
    return self.__sql
  def getColumnMap(self):
    return self.__columnMap
  def getDatas(self):
    return self.__datas
  def setDatas(self, datas):
    self.__datas = datas
  def isExists(self):
    return self.__exists
  def merge(self, tableDataInfo):
    datas = tableDataInfo.getDatas()
    if datas is not None:
      for data in datas:
        id = data.get('id')
        if id not in self.__dataMap:
          self.__datas.append(data)
          self.__dataMap[id] = data
    return self

# 获取pg数据库的数据
def getDataOfPg(tableName, connect, condition=None, orderBy=None):
  cur = connect.cursor()
  exists = tableExists(tableName, cur)
  if not exists:
    cur.close()
    return TableDataInfo(tableName, None, None, None, exists)
  sql = "SELECT * from {} WHERE (is_deleted=\'f\' or is_deleted=false )".format(tableName)
  if condition != None and len(condition)>0:
    sql = '{} and ({})'.format(sql, condition)
  if orderBy != None and len(orderBy)>0:
    sql = '{} order by {}'.format(sql, orderBy)
  else:
    #默认按id排序
    sql = sql + " order by lower(id)"
  cur.execute(sql)
  datas = cur.fetchall()
  tableInfo = TableDataInfo(tableName, cur.description, datas, sql)
  cur.close()
  return tableInfo

def tableExists(tableName, cur):
  sql = "SELECT relname FROM pg_class WHERE relname = \'{}\'".format(tableName);
  cur.execute(sql)
  datas = cur.fetchall()
  if(datas is None or len(datas) == 0):
    return False
  return True

# 解析yaml文件信息
def analysisYaml(yamlFile=None):
  if(yamlFile != None and len(yamlFile) > 0):
    fileName = yamlFile
  else:
    fileName = os.path.join(os.curdir, 'dbConfig.yaml').replace("\\", "/");
  f = open(fileName)
  dbConfigs = yaml.load(f, Loader=yaml.FullLoader)
  return dbConfigs


def getLocalConfig(yamlFile=None):
  if(yamlFile != None and len(yamlFile) > 0):
    fileName = yamlFile
  else:
    fileName = os.path.join(os.curdir, 'localhostConfig.yaml').replace("\\", "/");
  f = open(fileName)
  localConfig = yaml.load(f, Loader=yaml.FullLoader)
  return localConfig



#获取pg数据库连接
# dbInfo: 租户信息
# dbConfigs: 数据库配置信息
def getPgSql(dbInfo, dbConfigs):
  dbInfos = dbInfo.split(".")
  if len(dbInfos) < 2:
    print("ERROR: 请提供PG数据库的环境及数据库名称[{}]".format(dbInfo))
    sys.exit(1)

  envName = dbInfos[0]
  database = dbInfos[1]
  pgConfig = dbConfigs.get(envName,None)
  if pgConfig == None:
    print("ERROR:请配置PG数据库【{}】".format(envName))
    sys.exit(1)

  con = psycopg2.connect(database=database, user=pgConfig['user'], password=pgConfig['pwd'], host=pgConfig['host'], port=pgConfig['port'])
  return con


#重置本地库
# tableType: 需要恢复的表类型（multiList）
def revert_local_db(tableType):
  cmd = 'cd ddl;sh create_db.sh -f {}'.format(tableType)

  [result, msg] = subprocess.getstatusoutput(cmd)
  if result != 0:
    print("ERROR: 重置本地库失败！！！")
    print("[{}]{}".format(result, msg))
    sys.exit(1)


#检出指定分支代码
# projectName: 工程名称
# rootPath: 需要检出代码的工程根路径
# branch: 检出分支
def chectout_branch(projectName, rootPath, branchName):
  # TODO 如果要自动push则需要删除本地分支重新拉取
  if check_branch_exist(get_project(projectName), branchName) is None:
    print('ERROR: 工程【{}】不存在分支【{}】'.format(projectName, branchName))
    sys.exit(1)
  cmd = 'cd ' + rootPath + ';git checkout ' + branchName
  [result, msg] = subprocess.getstatusoutput(cmd)
  if result != 0:
    print("检出init-data[{}]分支报错！！！".format(branchName))
    print("[{}]{}".format(result, msg))
    sys.exit(1)

  [result, msg] = subprocess.getstatusoutput('cd ' + rootPath +'; git pull')
  if result != 0:
    print("检出init-data代码报错！！！")
    print("[{}]{}".format(result, msg))
    sys.exit(1)


#根据工程名称获取Gitlab工程对象
def get_project(projectName):
  gl = gitlab.Gitlab(URL, TOKEN)
  gl.auth()
  projects = gl.projects.list(search=projectName)
  if len(projects) > 0:
    for project in projects:
      if project.name_with_namespace.startswith("backend") and project.name == projectName:
        return project
  else:
    return None

#检查gitlab工程分支是否存在,并返回改分支对象
def check_branch_exist(project, branchName):
  try:
    return project.branches.get(branchName)
  except gitlab.exceptions.GitlabGetError:
    return None


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

#恢复预制文件的预制数据到指定的数据库---pg
# connect: pg数据库连接
# tableFiles: 文件数据
def execute_sql_pg(connect, tableFiles):
  cur = connect.cursor()
  for tableFile in tableFiles:
    file = Path(tableFile)
    if file.is_file():
      sqls = file.read_text('utf-8')
      if len(sqls.rstrip()) > 0:
        cur.execute(sqls)
    else:
      print("ERROR: SQL文件错误({})".format(tableFile))
  cur.close()
  connect.commit()
  return tableFiles

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

# 数据是否为空
# data: 需要判断的数据
def is_empty(data):
  if type(data) is str:
    return data is None or len(data.lstrip()) == 0
  else:
    return data is None or len(data) == 0

# if __name__ == "__main__":
#   # 获取预制环境
#   branch = check_branch_exist(get_project('init-data'), 'hotfix-inte')
#   print(json.dumps(branch))
