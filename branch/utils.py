# coding:utf-8
import os
import yaml
import gitlab
import sys
import subprocess
import re

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
URL='http://gitlab.q7link.com'
TOKEN=''

class ProjectInfo():
  def __init__(self, name, path, module):
    self.__name = name
    self.__path = path
    self.__module = module
    self.__project = None
    self.__checkPath()
    # self.fetch()# TODO 是否fetch

  def getName(self):
    return self.__name
  def getPath(self):
    return self.__path
  def getModule(self):
    return self.__module

  def __checkPath(self):
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path)
    if result != 0:
      print("ERROR: 工程【{}】路径【{}】不存在!!!".format(self.__name, self.__path))
      sys.exit(1)

  # 获取git仓库的项目信息
  def getProject(self):
    if self.__project is None:
      gl = gitlab.Gitlab(URL, TOKEN)
      try:
        gl.auth()
        projects = gl.projects.list(search=self.__name) # 此处是模糊查询
        if len(projects) > 0:
          for project in projects:
            if project.name_with_namespace.startswith("backend") and project.name == self.__name:
              self.__project = project
              break
      except Exception:
        print("项目：{}".format(self.__name))
        raise

    if self.__project is None:
      print("ERROR: 工程【{}】不存在!!!".format(self.__name))
      sys.exit(1)
    return self.__project

  # 获取远端git仓库的分支信息
  def getBranch(self, branchName):
    try:
      project = self.getProject()
      return project.branches.get(branchName)
    except gitlab.exceptions.GitlabGetError:
      return None

  # 删除分支保护
  def deleteBranchProtect(self, branchName):
    #获取受保护分支列表
    try:
      project = self.getProject()
      p_branch = project.protectedbranches.get(branchName)
      p_branch.delete()
    except gitlab.exceptions.GitlabGetError:
      pass
    finally:
      return True

  # 删除本地分支
  def deleteLocalBranch(self, deleteBranch, checkoutBranch=None):
    if checkoutBranch is None or len(checkoutBranch) == 0:
      subprocess.getstatusoutput('cd ' + self.__path +';git checkout ' + 'master')
    else:
      subprocess.getstatusoutput('cd ' + self.__path +';git checkout ' + checkoutBranch)
    subprocess.getstatusoutput('cd ' + self.__path +';git pull')
    #删除本地分支(使用-d，如果没有合并到当前分支，删除会报错)
    subprocess.getstatusoutput('cd ' + self.__path +';git branch -D ' + deleteBranch)

  # 删除远程分支
  def deleteRemoteBranch(self, deleteBranch):
    if(deleteBranch == 'master' or deleteBranch == 'stage'):
      print('ERROR: 【{}】分支不允许删除！！！！！！！！！！！'.format(deleteBranch))
      return False
    #删除分支保护
    self.deleteBranchProtect(deleteBranch)
    #删除分支
    self.getProject().branches.delete(deleteBranch)
    #刷新分支信息
    self.fetch()

  #设置分支保护
  def protectBranch(self, branchName, mergeAccessLevel, pushAccessLevel):
    # 删除分支保护
    self.deleteBranchProtect(branchName)
    self.getProject().protectedbranches.create({
      'name': branchName,
      'merge_access_level': mergeAccessLevel,
      'push_access_level': pushAccessLevel
    })

  #创建分支
  def createBranch(self, sourceBranchName, newBranchName):
    self.getProject().branches.create({'branch': newBranchName,'ref': sourceBranchName})

  #检查分支合并
  def checkMerge(self, sourceBranchName, targetBranchName):
    commits = self.getProject().repository_compare(targetBranchName,sourceBranchName).get('commits', [])
    if len(commits) == 0:
      return True
    else:
      return False

  #获取tag，如果未指定tag，则获取最新tag
  def getTag(self, tagName=None):
    if tagName is None or len(tagName) == 0:
      tags = self.getProject().tags.list();
      if len(tags) > 0:
        return tags[0]
      else:
        return None
    else:
      try:
        return self.getProject().tags.get(tagName)
      except gitlab.exceptions.GitlabGetError:
        return None

  #给指定分支打tag
  def createTag(self, name, branchName):
    try:
      tagName = '{}-{}'.format(name, branchName)
      self.getProject().tags.create({'tag_name':tagName,'ref':branchName})
    except Exception:
      print('工程【{}】分支【{}】打Tag【{}】失败！！！'.format(self.__name, branchName, tagName))
      raise

  #删除指定tag
  def deleteTag(self, tagName):
    try:
      self.getProject().tags.delete(tagName)
    except gitlab.exceptions.GitlabDeleteError:
      pass

  # 更新本地远程分支
  def fetch(self):
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +';git fetch -p')
    if result != 0:
      print(msg)
      sys.exit(1)

  # 检出指定分支
  def checkout(self, branchName):
    self.fetch()
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +';git checkout ' + branchName)
    if result != 0:
      print("WARNNING: 在路径【{}】检出分支【{}】失败！！！".format(self.__path, branchName))
      return False
    else:
      [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +';git pull')
      if result != 0:
        print(msg)
        return False
      return True

def project_path(names=None):
  # 获取path.yaml
  filename = os.path.join(os.curdir, 'path.yaml').replace("\\", "/")
  f = open(filename)
  projectConfigs = yaml.load(f, Loader=yaml.FullLoader)
  hasError = False
  projectInfos = {}
  for module,v in projectConfigs.items():
    for projectName,path in v.items():
      if names is None or len(names) == 0 or projectName in names or module in names:
        [result, msg] = subprocess.getstatusoutput('cd ' + path)
        if result != 0:
          print("ERROR: 工程【{}】路径【{}】不存在!!!".format(projectName, path))
          hasError = True
        else:
          #刷新每个工程的信息，防止因为本地信息和远程信息不同步导致报错
          # subprocess.getstatusoutput('cd ' + path +';git fetch -p')
          projectInfo = ProjectInfo(projectName, path, module)
          projectInfos[projectName] = projectInfo
  if hasError:
    return []
  else:
    return projectInfos

# #根据工程名称获取Gitlab工程对象
# def get_project(projectName):
#   gl = gitlab.Gitlab(URL, TOKEN)
#   try:
#     gl.auth()
#   except Exception:
#     print("项目：{}".format(projectName))
#     raise
#
#   projects = gl.projects.list(search=projectName)
#   if len(projects) > 0:
#     for project in projects:
#       if project.name_with_namespace.startswith("backend") and project.name == projectName:
#         return project
#   else:
#     return None

# #检查gitlab工程分支是否存在,并返回改分支对象
# def check_branch_exist(project, branchName):
#   try:
#     return project.branches.get(branchName)
#   except gitlab.exceptions.GitlabGetError:
#     return None

# #将本地分支删除，重新拉取远程分支
# def checkout_branch(path, branchName):
#   subprocess.getstatusoutput('cd ' + path +';git branch -D ' + branchName)
#   subprocess.getstatusoutput('cd ' + path +';git fetch -p')
#   [result, msg] = subprocess.getstatusoutput('cd ' + path +';git checkout ' + branchName)
#   if result != 0:
#     print("WARNNING: 在路径【{}】检出分支【{}】失败！！！".format(path, branchName))
#   else:
#     subprocess.getstatusoutput('cd ' + path +';git pull')

# #删除分支保护
# def delete_branch_protect(project, branchName):
#   #获取受保护分支列表
#   try:
#     p_branch = project.protectedbranches.get(branchName)
#     p_branch.delete()
#   except gitlab.exceptions.GitlabGetError:
#     return

#检查来源分支是否合并至目标分支
# def check_branch_merge(projectName, projectPath, sourceBranchName, targetBranchName):
#   subprocess.getstatusoutput('cd ' + projectPath +';git checkout ' + targetBranchName +';git pull')
#   [result, msg] = subprocess.getstatusoutput('cd ' + projectPath +';git fetch -p')
#   if result != 0:
#     # raise Exception('工程【{}】更新分支【{}】失败！！！！！！！！！！！'.format(projectName, targetBranchName))
#     print('ERROR: 工程【{}】更新分支信息失败！！！！！！！！！！！'.format(projectName))
#     return False
#   [result, msg] = subprocess.getstatusoutput('cd ' + projectPath +';git branch -r --merged origin/' + targetBranchName)
#   if result == 0:
#     branchName=''
#     length = len(msg)
#     for index in range(length):
#       char = msg[index]
#       if char == '\n' or (index + 1 == length):
#         if (index + 1 == length):
#           branchName += char
#         if ('origin/' + sourceBranchName == branchName):
#           return True
#         branchName = ''
#       elif char == ' ':
#         continue
#       else:
#         branchName += char
#     return False
#   else:
#     return False

#打印列表中的信息
def print_list(title, list):
  print(title)
  for index in range(len(list)):
   print ('  ' + str(index+1) +'.' + list[index])

#驼峰转换（将空格、_、-转换为驼峰）
def camel(s):
  s = re.sub(r"(\s|_|-)+", " ", s).title().replace(" ", "")
  return s[0].lower() + s[1:]

if __name__ == "__main__":
  print(camel("project-api"))
  print(camel("project"))
  print(camel("project api"))