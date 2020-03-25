# coding:utf-8
import os
import yaml
import gitlab
import sys
import subprocess

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
URL='http://52.81.114.94'
TOKEN=''

def project_path():
  # 获取path.yaml
  filename = os.path.join(os.curdir, 'path.yaml').replace("\\", "/")
  f = open(filename)
  projectPaths = yaml.load(f, Loader=yaml.FullLoader)
  hasError = False
  for k,v in projectPaths.items():
    [result, msg] = subprocess.getstatusoutput('cd ' + v)
    if result != 0:
      print("ERROR: 工程【{}】路径【{}】不存在".format(k, v))
      hasError = True
    else:
      #刷新每个工程的信息，防止因为本地信息和远程信息不同步导致报错
      subprocess.getstatusoutput('cd ' + v +';git fetch -p')
  if hasError:
    return []
  else:
    return projectPaths

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

#将本地分支删除，重新拉取远程分支
def checkout_branch(path, branchName):
  subprocess.getstatusoutput('cd ' + path +';git branch -D ' + branchName)
  subprocess.getstatusoutput('cd ' + path +';git fetch -p')
  [result, msg] = subprocess.getstatusoutput('cd ' + path +';git checkout ' + branchName)
  if result != 0:
    print("WARNNING: 在路径【{}】检出分支【{}】失败！！！".format(path, branchName))
  else:
    subprocess.getstatusoutput('cd ' + path +';git pull')

#删除分支保护
def delete_branch_protect(project, branchName):
  if(branchName == 'master'):
    print('ERROR: master分支不允许删除分支保护！！！！！！！！！！！')
    sys.exit(1)
  #获取受保护分支列表
  p_branches = project.protectedbranches.list()
  for branch in p_branches:
  	if branch.name == branchName:
  	  project.protectedbranches.delete(branchName)


#检查来源分支是否合并至目标分支
def check_branch_merge(projectName, projectPath, sourceBranchName, targetBranchName):
  subprocess.getstatusoutput('cd ' + projectPath +';git checkout ' + targetBranchName)
  [result, msg] = subprocess.getstatusoutput('cd ' + projectPath +';git fetch -p')
  if result != 0:
    # raise Exception('工程【{}】更新分支【{}】失败！！！！！！！！！！！'.format(projectName, targetBranchName))
    print('ERROR: 工程【{}】更新分支信息失败！！！！！！！！！！！'.format(projectName))
    return False
  [result, msg] = subprocess.getstatusoutput('cd ' + projectPath +';git branch -r --merged origin/' + targetBranchName)
  if result == 0:
    branchName=''
    length = len(msg)
    for index in range(length):
      char = msg[index]
      if char == '\n' or (index + 1 == length):
        if (index + 1 == length):
          branchName += char
        if ('origin/' + sourceBranchName == branchName):
          return True
        branchName = ''
      elif char == ' ':
        continue
      else: 
        branchName += char
    return False
  else:
    return False

#打印列表中的信息
def print_list(title, list):
  print(title)
  for index in range(len(list)):
   print ('  ' + str(index+1) +'.' + list[index])
