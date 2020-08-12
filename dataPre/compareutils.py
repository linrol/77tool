import json
import sys

def list_to_map(list):
  map = {}
  if list == None:
    return map
  else:
    for item in list:
      map[item['id']['value']]= item
    return map

# 对比产生升级脚本
def compare_and_genSql(tableName, newData=None, oldData=None):
  if newData != None or oldData != None:
    dataSqls = generate_sql(tableName, list_to_map(newData), list_to_map(oldData))

  dataNum = len(dataSqls)
  if dataNum > 0 :
    result = []
    result.append("--{} \n".format(tableName))
    result.append(dataSqls)
    result.append("\n \n \n")
    return result
  else:
    return None



# 生成SQL
def generate_sql(tableName, newDatas, oldDatas):
  olds = oldDatas.copy()
  news = newDatas.copy()
  update=[]
  insert=[]
  delete=[]
  for id,old in oldDatas.items():
    new = news.get(id, None)
    comment = ''

    if(tableName == 'baseapp_bill_type_template'):
      comment = '-- name[{}]  objectType[{}]\n'.format(old['name']['value'], old['object_type']['value'])
    elif tableName == 'baseapp_ui_config':
      comment = '-- name[{}]  type[{}]\n'.format(old['name']['value'], old['type']['value'])

    if(new == None):
      # 删除
      delete.append("--[{}][{}]\n".format(tableName, id) + comment + "delete from {} where id = \'{}\';\n".format(tableName, id))
      del olds[id]
    else:
      # 比较更新
      sql = compare_update(old, new, tableName)
      del olds[id]
      del news[id]
      if sql == None:
        continue
      else:
        # sql = sql.format("baseapp_bill_type_template")
        update.append("--[{}][{}]\n".format(tableName, id) + comment + sql)

  if len(news) > 0:
    # 新增
    for id,data in news.items():
      comment = ''
      sql = get_insert(data, tableName)
      if(tableName == 'baseapp_bill_type_template'):
        comment = '-- name[{}]  objectType[{}]\n'.format(data['name']['value'], data['object_type']['value'])
      elif tableName == 'baseapp_ui_config':
        comment = '-- name[{}]  type[{}]\n'.format(data['name']['value'], data['type']['value'])
      insert.append("--[{}][{}]\n".format(tableName, id) + comment + sql)

  result = []
  result.extend(delete)
  result.extend(insert)
  result.extend(update)
  if len(result) > 0:
    print("{}: 新增{}条，修改{}条，删除{}条".format(tableName, len(insert), len(update), len(delete)))
  return result


#对比并产生更新SQL
def compare_update(old, new, tableName):
  id = old['id']['value']
  if id != new['id']['value']:
    print("ERROR: id不一致不进行比对更新！！！")
    return None

  hasChange = False
  sql = 'update {} set '.format(tableName)
  for column, newValue in new.items():
    oldValue = old[column]
    if oldValue['value'] != newValue['value']:
      hasChange = True
      changeLog = differences_log(column, oldValue['value'], newValue['value'])
      sql = changeLog + sql + column + "=" + convert(newValue['value'], newValue['type'] == 3802) + " , "
    else:
      continue

  if hasChange:
    sql = sql[0:-3] + " where id = '{}';\n".format(id)
    return sql
  else:
    return None

def differences_log(column, oldValue, newValue):
  result = ''
  if oldValue == None:
    result = '--column[{}]字段赋值:【{}】\n'.format(column, newValue)
  elif type(oldValue) is int:
    result = '--column[{}]旧值:【{}】,新值:【{}】\n'.format(column, oldValue, newValue)
  elif type(oldValue) is float:
    result = '--column[{}]旧值:【{}】,新值:【{}】\n'.format(column, oldValue, newValue)
  elif type(oldValue) is bool:
    result = '--column[{}]旧值:【{}】,新值:【{}】\n'.format(column, oldValue, newValue)
  elif type(oldValue) is str:
    result = '--column[{}]旧值:【{}】,新值:【{}】\n'.format(column, oldValue, newValue)
  elif type(oldValue) is list:
    result = '--column[{}]旧值:【{}】,新值:【{}】\n'.format(column, oldValue, newValue)
  elif type(oldValue) is tuple:
    result = '--column[{}]旧值:【{}】,新值:【{}】\n'.format(column, oldValue, newValue)
  elif type(oldValue) is dict:
    for k,v in oldValue.items():
      result = '--column[{}]{}'.format(column,compare_dict(oldValue, newValue))
  elif type(oldValue) is set:
    result = '--column[{}]旧值:【{}】,新值:【{}】\n'.format(column, oldValue, newValue)
  else:
    print("ERROR: 未处理的类型[{}{}]".format(str(type(oldValue)), oldValue))
    sys.exit(1)
  return result

def compare_dict(old, new):
  result = ''
  if type(old) is dict and type(new) is dict:
    deleredKeys = old.keys() - new.keys()
    insertKeys = new.keys() - old.keys()
    if len(deleredKeys) > 0:
      result = '--删除的keys:' + str(deleredKeys) + "\n"
    if len(insertKeys) > 0:
      result += '--新增的keys:' + str(insertKeys) + "\n"
    updateKeys = old.keys() & new.keys()
    update = []
    for key in updateKeys:
      if old[key] != new[key]:
        update.append(key)
    if len(update) > 0:
      result += '--修改的keys:' + str(update) + "\n"

  else:
    result = '旧值：{},新值：{}'.format(old, new)
  return result

#根据数据生成插入SQL
def get_insert(data, tableName):
  head = 'INSERT INTO {} ( '.format(tableName)
  body = ') values ('

  for column, value in data.items():
    head = head + " \"" + column + "\","
    body = body + convert(value['value'], value['type'] == 3802) + ", "
  head = head +" \"created_time\", \"created_user_id\", \"is_init_data\", \"is_deleted\", \"last_modified_user_id\", \"last_modified_time\""
  body = body + "CURRENT_TIMESTAMP, \'1\', \'t\', \'f\', \'1\', CURRENT_TIMESTAMP);\n"
  sql = head + body
  return sql


#对数据进行格式转换
def convert(value, isJson):
  result = None
  if value == None:
    result = "null"
  elif type(value) is int:
    result = str(value)
  elif type(value) is float:
    result = str(value)
  elif type(value) is bool:
    if value:
      result = '\'t\''
    else:
      result = '\'f\''
  elif type(value) is str:
    if isJson:
      result = "\'\"{}\"\'".format(value.replace("\'", "\'\'"))
    else:
      result = "\'{}\'".format(value.replace("\'", "\'\'"))
  elif type(value) is list:
    result = "\'{}\'".format(json.dumps(value,ensure_ascii=False).replace("\'", "\'\'"))
  elif type(value) is tuple:
    result = "\'{}\'".format(json.dumps(value,ensure_ascii=False).replace("\'", "\'\'"))
  elif type(value) is dict:
    result = "\'{}\'".format(json.dumps(value,ensure_ascii=False).replace("\'", "\'\'"))
  elif type(value) is set:
    result = "\'{}\'".format(json.dumps(value,ensure_ascii=False).replace("\'", "\'\'"))
  else:
    print("ERROR: 未处理的类型[{}{}]".format(str(type(value)), value))
    sys.exit(1)
  return result

