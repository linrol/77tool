# coding=utf-8
import sys
import gitlab
import utils

#拉分支必须拉的工程
MUST_PROJECT={'apps': ['build']}
#拉各模块工程时，必须要拉取的工程
MODULE_PROJECT = {'platform': ['parent', 'testapp']}

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


#创建分支
def create_branch(projectInfo, sourceBranchName, newBranchName):
  projectInfo.createBranch(sourceBranchName, newBranchName)
  #设置分支保护
  protect_branch(projectInfo, newBranchName)
  #删除本地分支
  projectInfo.deleteLocalBranch(newBranchName)
  #在本地将新分支拉取出来
  projectInfo.checkout(newBranchName)

#获取需要创建的工程（返回：ProjectInfo对象数组）
def get_add_project(sourceBranchName, newBranchName, projectInfoMap, existCheck):
  error=[]
  adds=[]
  relatedModule={''}
  for projectName,projectInfo in projectInfoMap.items():
    if projectInfo is None:
      continue
    result = check_project(sourceBranchName, newBranchName, projectInfo, existCheck)
    if result.isAdd():
      adds.append(projectInfo)
      relatedModule.add(projectInfo.getModule())
    elif result.skip():
      print(result.getMessage())
    else:
      error.append(result.getMessage())

  projectConfigs = utils.project_config()
  # 拉取工程分支，自动拉取必须要拉的工程
  for module,projectNames in MUST_PROJECT.items():
    for projectName in projectNames:
      if not (projectName in projectInfoMap):
        path = projectConfigs.get(module, {}).get(projectName, None)
        projectInfo = utils.ProjectInfo(projectName, path, module)
        result = check_project(sourceBranchName, newBranchName, projectInfo, False)
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
        projectInfo = utils.ProjectInfo(projectName, path, module)
        result = check_project(sourceBranchName, newBranchName, projectInfo, False)
        if result.isAdd():
          adds.append(projectInfo)
          relatedModule.add(projectInfo.getModule())
        elif result.skip():
          print(result.getMessage())
        else:
          error.append(result.getMessage())

  if len(error) > 0:
    #如果有错误信息则不执行创建分支
    utils.print_list("ERROR: ", error)
    sys.exit(1)
  else:
    return adds

#检查工程目标分支是否符合创建条件
def check_project(sourceBranchName, newBranchName, projectInfo, existCheck):
  projectName = projectInfo.getName()

  if projectInfo.getPath() is None:
    errorMessgae = 'ERROR: 请在path.yaml文件配置工程【{}】路径！！！'.format(projectName)
    return CheckResult(projectInfo, False, errorMessgae)

  project = projectInfo.getProject()
  if project is None :
    errorMessgae = '工程【{}】不存在'.format(projectName)
    return CheckResult(projectInfo, False, errorMessgae)
  else:
    sourceBranch = projectInfo.getBranch(sourceBranchName)
    #来源分支存在才能拉取新分支
    if (sourceBranch is None):
      warnMessage = 'WARNING：工程【{}】来源分支【{}】不存在！！！！！！'.format(projectName, sourceBranchName)
      return CheckResult(projectInfo, True, warnMessage)
    else:
      newBranch = projectInfo.getBranch(newBranchName)
      if (newBranch is None):
        return CheckResult(projectInfo, False, None)
      else:
        if(existCheck):
          errorMessgae = '工程【{}】分支【{}】已存在'.format(projectName, newBranchName)
          return CheckResult(projectInfo, False, errorMessgae)
        else:
          projectInfo.checkout(newBranchName)
          warnMessage = 'WARNING：工程【{}】目标分支【{}】已存在！！！'.format(projectName, newBranchName)
          return CheckResult(projectInfo, True, warnMessage)


#设置分支保护
def protect_branch(projectInfo, branchName):
  #release、hotfix、emergency、stage-emergency、hotfix-inte、dev分支预先设置管理员全权限，便于修改版本号
  if branchName == 'release' or branchName == 'hotfix' or branchName == 'emergency' or branchName == 'stage-emergency' or branchName == 'hotfix-inte' or branchName == 'dev':
    mergeAccessLevel = gitlab.MAINTAINER_ACCESS
    pushAccessLevel = gitlab.MAINTAINER_ACCESS
    projectInfo.protectBranch(branchName, mergeAccessLevel, pushAccessLevel)
    print('工程【{}】分支【{}】保护成功'.format(projectInfo.getName(), branchName))
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

    #获取需操作工程的信息
    projectInfoMap = utils.project_path(projectNames)

    if len(projectInfoMap) > 0:
      #检查参数是否正确
      adds = get_add_project(sourceBranchName, newBranchName, projectInfoMap, existCheck)
      #创建分支
      for projectInfo in adds:
        try:
          create_branch(projectInfo, sourceBranchName, newBranchName)
        except Exception:
          print("项目：{}".format(projectInfo.getName()))
          raise
        print('工程【{}】基于分支【{}】创建分支【{}】成功'.format(projectInfo.getName(), sourceBranchName, newBranchName))
    else:
      print('ERROR: 请在path.yaml文件配置各工程路径！！！')
      sys.exit(1)
    