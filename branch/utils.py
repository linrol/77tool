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

DEVELOPER_ACCESS = 30
MAINTAINER_ACCESS = 40
VISIBILITY_PRIVATE = 0

class ProjectInfo():
  def __init__(self, name, path, module):
    self.__name = name
    self.__path = path
    self.__module = module
    self.__group = None
    self.__project = None
    self.__gl = self.getGl()
    self.__checkPath()
    # self.fetch()# TODO 是否fetch

  def getToken(self):
    return os.environ.get("GIT_TOKEN", TOKEN)
  def getGl(self):
    gl = gitlab.Gitlab(URL, self.getToken())
    gl.auth()
    return gl
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
      try:
        projects = self.__gl.projects.list(search=self.__name) # 此处是模糊查询
        if len(projects) > 0:
          for project in projects:
            if project.name_with_namespace.startswith("backend") and project.name == self.__name:
              self.__project = project
              break
            if project.name_with_namespace.startswith("front") and project.name == self.__name:
              self.__project = project
              break
      except Exception:
        print("项目：{}".format(self.__name))
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
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +' && git fetch -p')
    if result != 0:
      print(msg)
      sys.exit(1)

  # 检出指定分支
  def checkout(self, branchName):
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

  # 将分支分类
  def branchClass(self):
    self.fetch()
    branchs=[]
    [result, msg] = subprocess.getstatusoutput('cd ' + self.__path +' && git branch -vv')
    if result == 0 :
      #dev       a88c2c1 [origin/dev: behind 161] dev_dev-310-201912121945
      #master-1  1a0bc76 [origin/master: ahead 1, behind 1] 任务执行报告默认值设置
      branchInfos = msg.splitlines(False)
      for branchInfo in branchInfos:
        infos = branchInfo.lstrip().split(' ')
        isCurrent = False
        originBranchName = None
        originDeleted = False
        hasCommit = False
        hasPull = False
        branchName=''
        for index in range(len(infos)):
          info = infos[index]
          if info == '*':
            isCurrent = True
          elif info.startswith('[origin/'):
            originBranchName = info[info.find('/') + 1:-1]
            status = infos[index+1]
            if (status.startswith('gone') or status.startswith('丢失')):
              originDeleted= True
            elif (status.startswith('behind')):
              hasPull = True
            elif (status.startswith('ahead')):
              hasCommit = True
              if(infos[index+3].startswith('behind')):
                hasPull = True
          elif len(info) > 0 and len(branchName) == 0:
            branchName = info
        branch = LocalBranch(branchName, isCurrent, originBranchName, originDeleted, hasCommit, hasPull)
        branchs.append(branch)
      return branchs
    else:
      print('ERROR: 工程【{}】无法获取远程信息!!!'.format(self.__name))
      return branchs

  # 创建合并
  def createMrRequest(self, source, target, title, assignee):
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

  # 获取项目成员
  def getProjectMember(self, query):
    if query is None:
      return None
    members = self.getProject().members_all.list(query=query)
    if members is not None and len(members) > 0:
      return members[0]
    return None

class LocalBranch():
  def __init__(self, name, current, originBranchName, originDeleted, hasCommit, hasPull):
    self.__name = name
    self.__current = current
    self.__originBranchName = originBranchName
    self.__originDeleted = originDeleted
    self.__hasCommit = hasCommit
    self.__hasPull = hasPull

  def getName(self):
    return self.__name
  def isCurrent(self):
    return self.__current
  def hasOriginBranch(self):
    return self.__originBranchName is not None and len(self.__originBranchName) > 0
  def originBranchExists(self):
    return self.hasOriginBranch() and not self.__originDeleted
  def hasCommit(self):
    return self.__hasCommit
  def hasPull(self):
    return self.__hasPull

# 获取项目所属端
def get_project_end(projects):
  if projects is None:
    return "backend"
  if len(projects) < 1:
    return "backend"
  if projects in ["backend", "front"]:
    return projects
  front_projects = {"front-theory", "front-goserver", "front"}
  intersection = set(projects).intersection(front_projects)
  if len(intersection) > 0:
    return "front"
  return "backend"


def project_path(names=None):
  # 获取path.yaml
  projectConfigs = project_config(get_project_end(names))

  projectInfos = {}
  for module,v in projectConfigs.items():
    for projectName,path in v.items():
      if names is None or len(names) == 0 or projectName in names or module in names:
        #刷新每个工程的信息，防止因为本地信息和远程信息不同步导致报错
        # subprocess.getstatusoutput('cd ' + path +' && git fetch -p')
        projectInfo = ProjectInfo(projectName, path, module)
        projectInfos[projectName] = projectInfo
  return projectInfos

# 获取本地工程路径配置信息
def project_config(end=None):
  file = "path.yaml"
  if end is not None and end == "front":
    file = "path_front.yaml"
  filename = os.path.join(os.curdir, file).replace("\\", "/")
  f = open(filename)
  return yaml.load(f, Loader=yaml.FullLoader)

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