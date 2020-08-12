import json
import subprocess
import sys
import psycopg2
import os
import yaml
import gitlab

URL='http://52.81.114.94'
TOKEN='kiQ2sQENQVdRgkxzntQy'


excludeFields = ['last_criteria_value', 'entry_src_system_id', 'external_system_code', 'external_object_type', 'external_object_id', 'created_user_id', 'created_time', 'modified_user_id', 'modified_time', 'is_init_data', 'is_deleted', 'last_request_id', 'last_modified_user_id', 'last_modified_time', 'customized_fields','data_version']
# jsonFields = ['content']
# booleanFields = ['is_disabled','is_system','is_default','is_print','is_mobile','is_display','is_total','is_virtual','is_extend']
isSystemTable = ['baseapp_bill_type_template', 'baseapp_list_column', 'baseapp_list_column_schema', 'baseapp_list_columns_definition', 'baseapp_list_columns_schema', 'baseapp_list_columns_schema_context_field', 'baseapp_list_columns_schema_sort_field', 'baseapp_query_list_definition', 'baseapp_query_item', 'baseapp_query_item_schema', 'baseapp_query_definition', 'baseapp_query_schema', 'baseapp_query_definition_group','baseapp_list_column_group']

# 获取pg数据库的数据
def getDataOfPg(tableName, connect, condition=None, orderBy=None):
  cur = connect.cursor()
  sql = "SELECT * from {} WHERE (is_deleted=\'f\' or is_deleted=false )".format(tableName)
  if condition != None and len(condition)>0:
    sql = '{} and ({})'.format(sql, condition)
  if orderBy != None and len(condition)>0:
    sql = '{} order by {}'.format(sql, orderBy)
  else:
    #默认按id排序
    sql = sql + " order by id"
  cur.execute(sql)
  datas = cur.fetchall()
  results = []
  for data in datas:
    result = {}
    for index,field in enumerate(cur.description):
      field_name = field.name
      field_type = field.type_code
      if field_name not in excludeFields:
        result[field_name] = {}
        result[field_name]["type"] = field_type
        if field_type == 3802:
          #防止JSON中的中文转义，此处先转为字符串在转为JSON
          if data[index] != None:
            result[field_name]["value"] = json.loads(json.dumps(data[index]))
          else:
            result[field_name]["value"] = None
        elif field_name == 'is_system':
          #部分表的is_system字段需要默认设置为True
          if tableName in isSystemTable:
            result[field_name]["value"] = True
          else:
            result[field_name]["value"] = data[index]
        else:
          result[field_name]["value"] = data[index]

    results.append(result)
  cur.close()
  return results

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
    return projects[0]
  else:
    return None

#检查gitlab工程分支是否存在,并返回改分支对象
def check_branch_exist(project, branchName):
  try:
    return project.branches.get(branchName)
  except gitlab.exceptions.GitlabGetError:
    return None

if __name__ == "__main__":
  # 获取预制环境
  branch = check_branch_exist(get_project('init-data'), 'hotfix-inte')
  print(json.dumps(branch))
