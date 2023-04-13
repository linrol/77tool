# coding=utf-8
import sys
import gitlab
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import utils

EXCLUDE_PROJECT=['other','jsf','docs','finance','finance-api', 'dbtools', 'branch-manage', 'chrome-extension-backend', 'chrome-extension-backend-build']

class Refresh():
  # def __del__(self):
  #   if self.__connect is not None and not self.__connect.closed:
  #     # print("连接关闭")
  #     self.__connect.close()

  def __init__(self, branch, rootPath):
    self.__branch = branch
    self.__rootPath = rootPath
    self.clones = None
    self.namespaceMap= None
    self.pool = ThreadPoolExecutor(max_workers=10)

  def get_clone_projects(self):
    if self.namespaceMap is None:
      gl = gitlab.Gitlab(utils.URL, utils.TOKEN)
      gl.auth()
      projects = gl.projects.list(all=True, search_namespaces=True, search='backend')
      # projects = sorted(projects, key=lambda project: project.id)

      #key:namespace value:projectName集合
      namespaceMap = {}
      clones = []

      for project in projects:
        namespace = project.namespace['name']
        projectName = project.name
        if projectName in EXCLUDE_PROJECT or namespace in EXCLUDE_PROJECT:
          continue

        projectRootPath = self.__getProjectPath(project)
        if not self.__branchExists(project):
          continue

        #分支存在
        #记录存在分支的工程
        projectNames = namespaceMap.get(namespace, [])
        projectNames.append(projectName)
        namespaceMap[namespace]= projectNames

        #记录本地不存在工程的url
        if not self.projectPathExists(project, projectRootPath):
          # 不存在则，获取到本地
          httpUrl = project.http_url_to_repo
          clone = {'name':projectName, 'rootpath':projectRootPath, 'url':httpUrl}
          clones.append(clone)

        self.namespaceMap = namespaceMap
        self.clones = clones
    return self.clones


  # 获取工程所属文件夹
  def __getProjectPath(self, project):
    path = project.namespace['full_path'].replace('backend/', '')
    if len(path) > 0:
      return '{}{}'.format(self.__rootPath, path)
    else:
      return self.__rootPath

  # 检查分支是否存在
  def __branchExists(self, project):
    try:
      project.branches.get(self.__branch)
      return True
    except gitlab.exceptions.GitlabGetError:
      return False

  # 检查工程在本地是否存在
  def projectPathExists(self, project, projectRootPath):
    projectPath = '{}/{}'.format(projectRootPath, project.name)
    if os.path.exists(projectPath):
      return True
    else:
      if not os.path.exists(projectRootPath):
        os.makedirs(projectRootPath, 0o777)
      return False

  #克隆项目到本地并检出对应分支
  def __clone_and_checkout(self, clone):
      rootpath = clone['rootpath']
      url = clone['url']
      name = clone['name']
      [result, msg] = subprocess.getstatusoutput('cd {} && git clone {}'.format(rootpath, url))
      if(result != 0):
        print('ERROR: 克隆项目【{}】到本地失败：'.format(name))
        print (msg)
        sys.exit(1)
      if 'master' != self.__branch:
        #检出对应分支代码
        projectPath = '{}/{}'.format(rootpath, name)
        [result, msg] = subprocess.getstatusoutput('cd ' + projectPath +' && git fetch -p')
        if result != 0:
          print(msg)
          sys.exit(1)
        [result, msg] = subprocess.getstatusoutput('cd ' + projectPath +' && git checkout ' + self.__branch)
        if result != 0:
          print("WARNNING: 在路径【{}】检出分支【{}】失败！！！".format(projectPath, self.__branch))
          print(msg)
          sys.exit(1)
        else:
          [result, msg] = subprocess.getstatusoutput('cd ' + projectPath +' && git pull')
          if result != 0:
            print(msg)
            sys.exit(1)
      print('项目【{}】获取成功'.format(name))

  # 更新path.yaml文件
  def __updatePathYaml(self):
    if len(self.namespaceMap) > 0 and os.path.exists('./path.yaml'):
      file = os.path.join('./', 'path.yaml')
      with open(file,mode='w+',encoding='utf-8') as file:
        for groupName in sorted(self.namespaceMap):
          projectNames = self.namespaceMap[groupName]
          file.write('{}:\n'.format(groupName))
          for projectName in sorted(projectNames):
            file.write('  {}: {}{}/{}\n'.format(projectName, self.__rootPath, groupName, projectName))
          file.write('\n')

  def execute(self):
    clones = self.get_clone_projects()
    if len(clones) > 0:
      tasks = [self.pool.submit(self.__clone_and_checkout, clone) for clone in clones]
      wait(tasks, return_when=ALL_COMPLETED)
    self.__updatePathYaml()
    print("执行完成！！！")

#更新本地管理工具
#python3 refresh.py
if __name__ == "__main__":
  # if len(sys.argv) == 1 :
  #   branchName = 'master'
  #   rootPath = '../../'
  # elif len(sys.argv) == 2 :
  #   branchName =sys.argv[1]
  #   rootPath = '../../../' + branchName
  # elif len(sys.argv) == 3:
  #   branchName =sys.argv[1]
  #   if sys.argv[2].endswith('/'):
  #     rootPath =sys.argv[2] + branchName
  #   else:
  #     rootPath =sys.argv[2] + '/' + branchName
  # else:
  #   print ("ERROR: 输入参数错误, 正确的参数为：<branch> [<path>]")
  #   sys.exit(1)

  branchName = 'master'
  rootPath = '../../'

  executor = Refresh(branchName, rootPath)
  executor.execute()

