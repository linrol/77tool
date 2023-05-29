# coding=utf-8
import sys
import utils
import traceback
import re
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED


#拉分支必须拉的工程
MUST_PROJECT={'apps': ['build']}
#拉各模块工程时，必须要拉取的工程
MODULE_PROJECT = {'platform': ['parent', 'testapp']}
#拉工程时，依赖要拉取的工程
DEPEND_PROJECT = {'base-common': ['base-common-test']}

BRANCH_REGEX=r'^(sprint|emergency|stage-patch|release)20[2-9][0-9][0-1][0-9][0-3][0-9]$'

class CheckResult():
  def __init__(self, projectInfo, skip, message):
    self.__projectInfo = projectInfo
    self.__skip = skip
    self.__message = message

  def getProjectInfo(self):
    return self.__projectInfo
  #是否跳过不创建分支
  def skip(self):
    return self.__skip
  # 是否检查通过，允许创建分支
  def isAdd(self):
    return (not self.__skip) and (self.__message is None or len(self.__message) == 0)
  #错误信息
  def getMessage(self):
    return self.__message

class CreateBranch:
  def __init__(self, newBranchName, sourceBranchName, projectNames=None, existCheck = True):
    self.newBranchName = newBranchName
    self.sourceBranchName = sourceBranchName
    self.projectNames = projectNames
    self.existCheck = existCheck#是否检查分支存在（false:分支存在则不创建，不存在则创建；true:分支存在则报错，所有工程不创建分支）
    self.pool = ThreadPoolExecutor(max_workers=10)

  def execute(self):
    #获取需操作工程的信息
    projectInfoMap = utils.project_path(self.projectNames)

    if len(projectInfoMap) > 0:
      #检查参数是否正确
      adds = self.get_add_project(projectInfoMap)
      #创建分支
      if len(adds) > 0 :
        tasks = [self.pool.submit(self.create_branch, projectInfo) for projectInfo in adds]
        wait(tasks, return_when=ALL_COMPLETED)
      return ",".join(list(map(lambda add: add.getName(), adds)))
    else:
      print('ERROR: 请在path.yaml文件配置各工程路径！！！')
      sys.exit(1)

  #创建分支
  def create_branch(self, projectInfo):
    source_branch = self.sourceBranchName
    try:
      source_branch = projectInfo.createBranch(self.sourceBranchName, self.newBranchName)
      #设置分支保护
      self.protect_branch(projectInfo)
      #删除本地分支
      projectInfo.deleteLocalBranch(self.newBranchName)
      #在本地将新分支拉取出来
      projectInfo.checkout(self.newBranchName)
    except Exception as e:
      print("ERROR: 项目：{}".format(projectInfo.getName()))
      traceback.print_exc()
    print('工程【{}】基于分支【{}】创建分支【{}】成功'.format(projectInfo.getName(), source_branch, self.newBranchName))

  #获取需要创建的工程（返回：ProjectInfo对象数组）
  def get_add_project(self, projectInfoMap):
    error=[]
    adds=[]
    relatedModule=set()
    tasks = [self.pool.submit(self.check_project, projectInfo, self.existCheck) for projectInfo in projectInfoMap.values()]
    for future in as_completed(tasks):
      result = future.result()
      if result.isAdd():
        projectInfo = result.getProjectInfo()
        adds.append(projectInfo)
        relatedModule.add(projectInfo.getModule())
      elif result.skip():
        print(result.getMessage())
      else:
        error.append(result.getMessage())

    projectConfigs = utils.project_config()
    # 拉取工程分支，自动拉取必须要拉的工程
    if "front" not in relatedModule and len(relatedModule) > 0:
      for module,projectNames in MUST_PROJECT.items():
        for projectName in projectNames:
          if not (projectName in projectInfoMap):
            path = projectConfigs.get(module, {}).get(projectName, None)
            projectInfo = utils.ProjectInfo(projectName, path, module)
            result = self.check_project(projectInfo, False)
            if result.isAdd():
              adds.append(projectInfo)
              relatedModule.add(projectInfo.getModule())
            elif result.skip():
              print(result.getMessage())
            else:
              error.append(result.getMessage())

    # 拉取某个模块的工程时，自动拉取该模块下的必须要拉的工程
    for module,projectNames in MODULE_PROJECT.items():
      if module in relatedModule:
        for projectName in projectNames:
          if not (projectName in projectInfoMap):
            path = projectConfigs.get(module, {}).get(projectName, None)
          else:
            continue
          projectInfo = utils.ProjectInfo(projectName, path, module)
          result = self.check_project(projectInfo, False)
          if result.isAdd():
            adds.append(projectInfo)
            relatedModule.add(projectInfo.getModule())
          elif result.skip():
            print(result.getMessage())
          else:
            error.append(result.getMessage())

    # 拉取某个工程时，自动拉依赖的工程
    for project,projectNames in DEPEND_PROJECT.items():
      if project in list(map(lambda p: p.getName(), adds)):
        for projectName in projectNames:
          module = "apps"
          if not (projectName in projectInfoMap):
            path = projectConfigs.get(module, {}).get(projectName, None)
          else:
            continue
          projectInfo = utils.ProjectInfo(projectName, path, module)
          result = self.check_project(projectInfo, False)
          if result.isAdd():
            adds.append(projectInfo)
            relatedModule.add(projectInfo.getModule())
          elif result.skip():
            print(result.getMessage())
          else:
            error.append(result.getMessage())

    if len(error) > 0:
      #如果有错误信息则不执行删除
      utils.print_list("ERROR: ", error)
      sys.exit(1)
    else:
      return adds


  #检查工程目标分支是否符合创建条件
  def check_project(self, projectInfo, existCheck):
    projectName = projectInfo.getName()

    if projectInfo.getPath() is None:
      errorMessgae = 'ERROR: 请在path.yaml文件配置工程【{}】路径！！！'.format(projectName)
      return CheckResult(projectInfo, False, errorMessgae)

    project = projectInfo.getProject()
    if project is None :
      errorMessgae = '工程【{}】不存在'.format(projectName)
      return CheckResult(projectInfo, False, errorMessgae)
    else:
      sourceBranch = projectInfo.getBranch(self.sourceBranchName)
      #来源分支存在才能拉取新分支
      if (sourceBranch is None):
        warnMessage = 'WARNNING：工程【{}】来源分支【{}】不存在！！！！！！'.format(projectName, self.sourceBranchName)
        return CheckResult(projectInfo, True, warnMessage)
      else:
        newBranch = projectInfo.getBranch(self.newBranchName)
        if (newBranch is None):
          return CheckResult(projectInfo, False, None)
        else:
          if(existCheck):
            errorMessgae = '工程【{}】分支【{}】已存在'.format(projectName, self.newBranchName)
            return CheckResult(projectInfo, False, errorMessgae)
          else:
            projectInfo.checkout(self.newBranchName)
            warnMessage = 'WARNNING：工程【{}】目标分支【{}】已存在！！！'.format(projectName, self.newBranchName)
            return CheckResult(projectInfo, True, warnMessage)


  #设置分支保护
  def protect_branch(self, projectInfo):
    #release、hotfix、emergency、stage-emergency、hotfix-inte、dev分支预先设置管理员全权限，便于修改版本号
    if re.match(BRANCH_REGEX, self.newBranchName) is not None or self.newBranchName in ['release', 'hotfix', 'emergency', 'stage-emergency', 'hotfix-inte', 'dev']:
      mergeAccessLevel = utils.MAINTAINER_ACCESS
      pushAccessLevel = utils.MAINTAINER_ACCESS
      projectInfo.protectBranch(self.newBranchName, mergeAccessLevel, pushAccessLevel)
      # print('工程【{}】分支【{}】保护成功'.format(projectInfo.getName(), self.newBranchName))
    else:
      #其他分支不设置分支保护
      return

#创建工程分支
#python3 createBranch.py master hotfix fiance build init-data
if __name__ == "__main__":
  if len(sys.argv) < 3 :
    print ("ERROR: 输入参数错误, 正确的参数为：<source branch> <new branch> [<projectName>...]")
    sys.exit(1)
  else:
    projectNames =[]
    if len(sys.argv) > 3:
      projectNames = sys.argv[3:]

    sourceBranchName = sys.argv[1]
    newBranchName = sys.argv[2]

    existCheck = True#是否检查分支存在（false:分支存在则不创建，不存在则创建；true:分支存在则报错，所有工程不创建分支）
    infos=newBranchName.split('.')
    if len(infos) > 1:
      newBranchName = infos[0]
      existCheck = (infos[1].lower() != 'false')

    executor = CreateBranch(newBranchName, sourceBranchName, projectNames, existCheck)
    executor.execute()