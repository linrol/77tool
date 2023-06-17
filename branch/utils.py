# coding:utf-8
import os
import yaml
import gitlab
import sys
import subprocess
import re
import time
import xml.dom.minidom
import requests
import json

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
URL='http://gitlab.q7link.com'
VERSION = "1.0.0"
TOKEN=''

DEVELOPER_ACCESS = 30
MAINTAINER_ACCESS = 40
VISIBILITY_PRIVATE = 0

class ProjectInfo():
  def __init__(self, end, module, name, config):
    self.__end = end
    self.__name = name
    self.__path = config.get("path")
    self.__module = module
    self.__namespace = config.get("namespace", None)
    self.__group = None
    self.__project = None
    self.__gl = self.getGl()
    self.__checkPath(config.get("checkPath", True))
    # self.fetch()# TODO 是否fetch

  def getToken(self):
    return os.environ.get("GIT_TOKEN", TOKEN)
  def getGl(self):
    gl = gitlab.Gitlab(URL, self.getToken())
    gl.auth()
    return gl
  def getEnd(self):
    return self.__end
  def getName(self):
    return self.__name
  def getPath(self):
    return self.__path
  def getModule(self):
    return self.__module

  def __checkPath(self, check):
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path)
    if result == 0:
      return
    if not check:
      self.__path = None
    else:
      print("ERROR: 工程【{}】路径【{}】不存在!!!".format(self.__name, self.__path))
      sys.exit(1)

  # 获取git仓库的项目信息
  def getProject(self):
    if self.__project is None:
      try:
        if self.__namespace is not None:
          projects = self.__gl.projects.get(self.__namespace)
        else:
          projects = self.__gl.projects.list(search=self.__name) # 此处是模糊查询
        if len(projects) == 1:
          self.__project = projects[0]
        if len(projects) > 1:
          for project in projects:
            if project.name_with_namespace.startswith("backend") and project.name == self.__name:
              self.__project = project
              break
            if project.name_with_namespace.startswith("front") and project.name == self.__name:
              self.__project = project
              break
      except Exception:
        # print("从git获取项目失败：{}".format(self.__name))
        raise
    if self.__project is None:
      print("ERROR: 工程【{}】不存在!!!".format(self.__name))
      sys.exit(1)
    return self.__project

  def getGroup(self, group_name=None):
    if group_name is None:
      group_name = self.__module
    if self.__group is None:
      try:
        groups = self.__gl.groups.list(search=group_name) # 此处是模糊查询
        if len(groups) > 0:
          for group in groups:
            if group.full_path.startswith("backend") and group.name == group_name:
              self.__group = group
              break
      except Exception:
        print("群组：{}".format(self.__group))
        raise

    if self.__group is None:
      print("ERROR: 群组【{}】不存在!!!".format(group_name))
      sys.exit(1)
    return self.__group

  # 获取远端git仓库的分支信息
  def getBranch(self, branchNames):
    for branch in branchNames.split("."):
      try:
        project = self.getProject()
        return project.branches.get(branch)
      except gitlab.exceptions.GitlabGetError:
        pass
    return None

  # 获取分支是否存在交集
  def branchIntersection(self, branchNames):
    for branch in branchNames:
      if self.getBranch(branch) is None:
        return False
    return True


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
    if self.__path is None:
      return
    if checkoutBranch is None or len(checkoutBranch) == 0:
      [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +' && git status')
      if(result == 0):
        if (msg.splitlines(False)[0]).endswith(deleteBranch):
          if deleteBranch == 'master':
            subprocess.getstatusoutput('cd ' + self.__path +' && git checkout stage')
          else:
            subprocess.getstatusoutput('cd ' + self.__path +' && git checkout master')
    else:
      subprocess.getstatusoutput('cd ' + self.__path +' && git checkout ' + checkoutBranch)
    subprocess.getstatusoutput('cd ' + self.__path +' && git pull')
    #删除本地分支(使用-d，如果没有合并到当前分支，删除会报错)
    subprocess.getstatusoutput('cd ' + self.__path +' && git branch -D ' + deleteBranch)

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
    if mergeAccessLevel == VISIBILITY_PRIVATE:
      mergeRole = "No one"
    elif mergeAccessLevel == DEVELOPER_ACCESS:
      mergeRole = "Developers + Maintainers"
    else:
      mergeRole = "Maintainers"
    if pushAccessLevel == VISIBILITY_PRIVATE:
      pushRole = "No one"
    elif pushAccessLevel == DEVELOPER_ACCESS:
      pushRole = "Developers + Maintainers"
    else:
      pushRole = "Maintainers"
    return True, mergeRole, pushRole

  #创建分支
  def createBranch(self, sourceBranchNames, newBranchName):
    for branch in sourceBranchNames.split("."):
      try:
        self.getProject().branches.create({'branch': newBranchName,'ref': branch})
        return branch
      except gitlab.exceptions.GitlabCreateError:
        pass
    return None

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
      tags = self.getProject().tags.list()
      if len(tags) > 0:
        return tags[0]
      else:
        return None
    else:
      try:
        return self.getProject().tags.get(tagName)
      except gitlab.exceptions.GitlabGetError:
        return None

  def getLastTag(self):
    tags = self.getProject().tags.list()
    if len(tags) > 0:
      return tags[0]
    return None

  #给指定分支打tag
  def createTag(self, tagName, branchName):
    try:
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
    if self.__path is None:
      return
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +' && git fetch -p')
    if result != 0:
      print(msg)
      sys.exit(1)

  # 检出指定分支
  def checkout(self, branchName):
    if self.__path is None:
      return True
    self.fetch()
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +' && git checkout ' + branchName)
    if result != 0:
      print("WARNNING: 在路径【{}】检出分支【{}】失败！！！".format(self.__path, branchName))
      return False
    else:
      [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +' && git pull')
      if result != 0:
        print(msg)
        return False
      return True

  # 检出指定分支
  def checkoutTag(self, tagName):
    if self.__path is None:
      return True
    self.fetch()
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +' && git checkout ' + tagName)
    if result != 0:
      print("WARNNING: 在路径【{}】检出分支【{}】失败！！！".format(self.__path, tagName))
      return False
    else:
      return True

  # 创建合并
  def createMr(self, source, target, title, assignee):
    data = {
    'source_branch': source,
    'target_branch': target,
    'title': title,
    'remove_source_branch': True
    }
    member = self.getProjectMember(assignee)
    if member is not None:
      data['assignee_id'] = member.id
    return self.getProject().mergerequests.create(data)

  def getMr(self, mr_iid):
    return self.getProject().mergerequests.get(mr_iid)

  # 检查合并冲突，借助gitlab的发起mr来判断
  def checkConflicts(self, source, target, title):
    mr = self.createMr(source, target, title, None)
    elapsed = 0
    while True:
      mr = self.getMr(mr.iid)
      status = mr.merge_status
      if status == 'can_be_merged':
        mr.delete()
        return False
      if status in ['cannot_be_merged', 'cannot_be_merged_recheck']:
        mr.delete()
        return True
      if elapsed > 30:
        mr.delete()
        return True
      elapsed += 3
      time.sleep(3)

  # 接受合并
  def acceptMr(self, mr):
    project_full = mr.references.get("full").split("!")[0]
    _, project = project_full.rsplit("/", 1)
    source = mr.source_branch
    target = mr.target_branch
    if mr.merged_at is not None or mr.merged_by is not None:
      raise Exception("工程【】从【】已合并至【】，请不要重复合并", project, source, target)
    if mr.has_conflicts or mr.merge_status != "can_be_merged":
      raise Exception("工程【】从【】合并至【】存在冲突", project, source, target)
    return mr.merge()

  # 获取项目成员
  def getProjectMember(self, query):
    if query is None:
      return None
    members = self.getProject().members_all.list(query=query)
    if members is not None and len(members) > 0:
      return members[0]
    return None

def check_upgrade():
  try:
    response = requests.get("http://branch.q7link.com/check/upgrade?version=" + VERSION)
    if response.status_code != 200:
      return
    body = json.loads(response.text)
    ret = body.get('ret')
  except Exception:
    return
  if not ret:
    raise Exception("分支管理工具必须更新后可用")


def init_projects(names=None):
  check_upgrade()
  if names is None or len(names) == 0:
    names = ["backend"]
  projectInfos = {}
  for end, modules in project_config().items():
    for module, projects in modules.items():
      for project, config in projects.items():
        match_name = project in names
        match_module = module in names
        match_end = end in names
        if match_name or match_module or match_end:
          # 刷新每个工程的信息，防止因为本地信息和远程信息不同步导致报错
          # subprocess.getstatusoutput('cd ' + path +' && git fetch -p')
          projectInfo = ProjectInfo(end, module, project, config)
          projectInfos[project] = projectInfo
  return projectInfos

# 获取本地工程路径配置信息
def project_config():
  with open("./project.json", "r", encoding="utf-8") as f:
    content = json.load(f)
  return content

#打印列表中的信息
def print_list(title, list):
  print(title)
  for index in range(len(list)):
   print ('  ' + str(index+1) +'.' + list[index])

#驼峰转换（将空格、_、-转换为驼峰）
def camel(s):
  s = re.sub(r"(\s|_|-)+", " ", s).title().replace(" ", "")
  return s[0].lower() + s[1:]

def yaml_parse(bytes):
  return yaml.load(bytes, Loader=yaml.FullLoader)

def pom_parse(bytes):
  return xml.dom.minidom.parseString(bytes)

def get_project_file(project, branch, file_path, parser):
  f = project.getProject().files.get(file_path=file_path, ref=branch)
  if f is None:
    raise Exception("工程【{}】分支【{}】不存在文件【{}】".format(project,
                                                            branch,
                                                            file_path))
  return parser(f.decode())

if __name__ == "__main__":
  print(camel("project-api"))
  print(camel("project"))
  print(camel("project api"))