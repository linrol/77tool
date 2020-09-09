import subprocess
import sys
import time
import os
import json
from pathlib import Path

sys.path.append(r"../../branch-manage")
from dataPre import utils
from dataPre import multi
from dataPre import form
from dataPre import billtype
from dataPre import resetForm


if __name__ == "__main__":
  # 获取预制类型
  preTypeMap = {"1":"form","2":"multiList","3":"billType","4":"reset"}
  print("预制数据类型：")
  print("   1.前端表单模板")
  print("   2.前端多列表方案")
  print("   3.前端单据类型模板")
  print("   4.重置表单数据")
  str = input("请选择需要预制的数据：")
  preType = preTypeMap.get(str, None)
  if preType == None :
    print("ERROR:请选择正确的预制数据类型【{}】".format(preType))
    sys.exit(1)

  # 获取预制环境
  envMap = {"1":"hotfix-inte","2":"hotfix-db","3":"hotfix-emergency","4":"reports", "5":"release", "6":"release-db", "7":"hotfix"}
  if preType == 'reset':
    print("预制数据来源环境：")
  else:
    print("重置环境：")

  for k, v in envMap.items():
    print("   "+ k + "." + v)
  print("   自定义(例：dev)")
  if preType == 'reset':
    str = input("请选择需要重置表单数据的环境：")
  else:
    str = input("请选择预制数据来源环境：")
  env = envMap.get(str, None)
  if env == None :
    env = str

  dbConfigs = utils.analysisYaml()
  # 获取环境配置信息
  pgConfig = dbConfigs.get(env,None)
  if pgConfig == None:
    print("ERROR:请配置PG数据库【{}】".format(env))
    sys.exit(1)
  branch = pgConfig.get('branch', None)
  #根据预制类型获取租户id
  tenantId = pgConfig.get('tenantId', {}).get(preType, None)

  # 代码分支确认
  if branch is None or len(branch.rstrip())==0:
    if preType == 'reset':
      branch = input("请输入表单数据的代码分支：")
    else:
      branch = input("请输入要预制的代码分支：")
  else :
    print("代码分支：")
    print("   1." + branch)
    print("     自定义(例:dev)")
    str = input("请输入代码分支：")
    if str != "1":
      branch = str

  # 预制租户确认
  if tenantId is None:
    if preType == 'reset':
      tenantId = input("请输入" + env + "要重置的租户ID：")
    else:
      tenantId = input("请输入" + env + "的预制租户ID：")
  else :
    print("预制租户ID：")
    print("   1.1")
    print("   2." + tenantId)
    print("     自定义(例:MQD34N501EX0001)")
    str = input("请选择租户：")
    if str != "2":
      tenantId = str

  # 多列表方案预置必须输入查询条件
  condition = None
  if preType == 'multiList':
    # 查询条件
    condition = pgConfig.get('condition', None)
    if condition is None or len(condition.rstrip())==0:
      condition = input("请输入查询条件(主表:baseapp_query_definition_group):")
    else:
      print("查询条件：")
      print("   1." + condition)
      print("     自定义(例:name = 'Timesheet_list')")
      str = input("请输入查询条件(主表:baseapp_query_definition_group):")
    if condition is None or len(condition.rstrip())==0:
      print("ERROR:请数据查询条件")
      sys.exit(1)
    elif str != '1':
      condition = str

  #提交人
  if preType != 'reset':
    commitUser = input("请输入提交人（若不进行提交则不输入）:")

  # 执行
  if preType == 'multiList':
    multi.pre_multi_list(env, "tenant"+tenantId, branch, commitUser, condition)
  elif preType == 'form':
    form.pre_form(env, "tenant"+tenantId, branch, commitUser)
  elif preType == 'billType':
    billtype.pre_bill_type(env, "tenant"+tenantId, branch, commitUser)
  elif preType == 'reset':
    resetForm.reset_form(env, "tenant"+tenantId, branch)
