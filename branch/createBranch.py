# coding=utf-8
import sys
import gitlab
import utils

#创建分支
def create_branch(sourceBranchName, newBranchName, project, projectInfo):
  project.branches.create({'branch': newBranchName,'ref': sourceBranchName})
  #设置分支保护
  protect_branch(newBranchName, project)
  #在本地将新分支拉取出来
  utils.checkout_branch(projectInfo.getPath(), newBranchName)

#检查参数是否正确（返回：key:gitlab的project对象，value:本地工程路径）
def check_project(sourceBranchName, newBranchName, projectNames, projectInfoMap, existCheck):
  error=[]
  projectMap={}
  for projectName,projectInfo in projectInfoMap.items():
    if projectInfo is None or (projectName not in projectNames and projectInfo.getModule() not in projectNames):
      continue

    if projectInfo.getPath() is None:
      error.append('ERROR: 请在path.yaml文件配置工程【{}】路径！！！'.format(projectName))
      continue

    project = utils.get_project(projectName)
    if project is None :
      error.append('工程【{}】不存在'.format(projectName))
    else:
      sourceBranch = utils.check_branch_exist(project, sourceBranchName)
      #来源分支存在才能拉取新分支
      if (sourceBranch is None):
        print('WARNING：工程【{}】来源分支【{}】不存在！！！！！！'.format(projectName, sourceBranchName))
      else:
        newBranch = utils.check_branch_exist(project, newBranchName)
        if (newBranch is None):
          projectMap[project] = projectInfo
        else:
          if(existCheck):
            error.append('工程【{}】分支【{}】已存在'.format(projectName, newBranchName))
          else:
            print('WARNING：工程【{}】目标分支【{}】已存在！！！'.format(projectName, sourceBranchName))

  if len(error) > 0:
    #如果有错误信息则不执行创建分支
    utils.print_list("ERROR: ", error)
    sys.exit(1)
  else:
    return projectMap

#设置分支保护
def protect_branch(branchName, project):
  utils.delete_branch_protect(project, branchName)
  #release、hotfix、emergency、stage-emergency、hotfix-inte、dev分支预先设置管理员全权限，便于修改版本号
  if branchName == 'release' or branchName == 'hotfix' or branchName == 'emergency' or branchName == 'stage-emergency' or branchName == 'hotfix-inte' or branchName == 'dev':
    mergeAccessLevel = gitlab.MAINTAINER_ACCESS
    pushAccessLevel = gitlab.MAINTAINER_ACCESS

    p_branch = project.protectedbranches.create({
      'name': branchName,
      'merge_access_level': mergeAccessLevel,
      'push_access_level': pushAccessLevel
    })
    print('【{}】【{}】分支保护成功'.format(project.name, p_branch.name))
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
    #获取所有工程的本地路径
    projectInfoMap = utils.project_path()
    projectNames =[]
    if len(sys.argv) > 3:
      projectNames = sys.argv[3:]
    else:
      projectNames = list(projectInfoMap.keys())

    sourceBranchName = sys.argv[1]
    newBranchName = sys.argv[2]

    existCheck = True#是否检查分支存在（false:分支存在则不创建，不存在则创建；true:分支存在则报错，所有工程不创建分支）
    infos=newBranchName.split('.')
    if len(infos) > 1:
      newBranchName = infos[0]
      existCheck = (infos[1].lower() != 'false')

    if len(projectInfoMap) > 0:
      #检查参数是否正确
      projectMap = check_project(sourceBranchName, newBranchName, projectNames, projectInfoMap, existCheck)
      #创建分支
      for k,v in projectMap.items():
        try:
          create_branch(sourceBranchName, newBranchName, k, v)
        except Exception:
          print("项目：{}".format(k.name))
          raise
        print('工程【{}】基于分支【{}】创建分支【{}】成功'.format(k.name, sourceBranchName, newBranchName))
    else:
      print('ERROR: 请在path.yaml文件配置各工程路径！！！')
      sys.exit(1)
    