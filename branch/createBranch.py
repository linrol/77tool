# coding=utf-8
import sys
import gitlab
import utils

#创建分支
def create_branch(sourceBranchName, newBranchName, project, path):
  project.branches.create({'branch': newBranchName,'ref': sourceBranchName})
  #设置分支保护
  protect_branch(newBranchName, project)
  #在本地将新分支拉取出来
  utils.checkout_branch(path, newBranchName)

#检查参数是否正确（返回：key:gitlab的project对象，value:本地工程路径）
def check_project(sourceBranchName, newBranchName, projectNames, projectPaths):
  error=[]
  projectMap={}
  for projectName in projectNames:
    projectPath = projectPaths.get(projectName, None)
    if projectPath is None:
      error.append('ERROR: 请在path.yaml文件配置工程【{}】路径！！！'.format(projectName))
      continue

    project = utils.get_project(projectName)
    if project is None :
      error.append('工程【{}】不存在'.format(k))
    else:
      sourceBranch = utils.check_branch_exist(project, sourceBranchName)
      #来源分支存在才能拉取新分支
      if (sourceBranch is None):
        error.append('工程【{}】分支【{}】不存在'.format(projectName, sourceBranchName))
      else:
        newBranch = utils.check_branch_exist(project, newBranchName)
        if (newBranch is None):
          projectMap[project] = projectPaths[projectName]
        else:
          error.append('工程【{}】分支【{}】已存在'.format(projectName, newBranchName))
  if len(error) > 0:
    #如果有错误信息则不执行创建分支
    utils.print_list("ERROR: ", error)
    sys.exit(1)
  else:
    return projectMap

#设置分支保护
def protect_branch(branchName, project):
  projectName = project.name
  utils.delete_branch_protect(project, branchName)
  mergeAccessLevel = gitlab.DEVELOPER_ACCESS
  pushAccessLevel = gitlab.DEVELOPER_ACCESS
  #release、hotfix、emergency、hotfix-emergency、hotfix-inte分支预先设置管理员全权限，便于修改版本号
  if branchName == 'release' or branchName == 'hotfix' or branchName == 'emergency' or branchName == 'hotfix-emergency' or branchName == 'hotfix-inte':
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
  # elif branchName == 'hotfix' or branchName == 'emergency':
  #   if projectName == 'build' or projectName == 'init-data':
  #     mergeAccessLevel = gitlab.MAINTAINER_ACCESS
  #     pushAccessLevel = gitlab.MAINTAINER_ACCESS
  #   else:
  #     mergeAccessLevel = gitlab.MAINTAINER_ACCESS
  #     pushAccessLevel = 0




#创建工程分支
#python3 createBranch.py master hotfix fiance build init-data
if __name__ == "__main__":
  if len(sys.argv) < 3 :
    print ("ERROR: 输入参数错误, 正确的参数为：<source branch> <new branch> [<projectName>...]")
    sys.exit(1)
  else:
    #获取所有工程的本地路径
    projectPaths = utils.project_path()
    projectNames =[]
    if len(sys.argv) > 3:
      projectNames = sys.argv[3:]
    else:
      projectNames = list(projectPaths.keys())

    sourceBranchName = sys.argv[1]
    newBranchName = sys.argv[2]
    if len(projectPaths) > 0:
      #检查参数是否正确
      projectMap = check_project(sourceBranchName, newBranchName, projectNames, projectPaths)
      #创建分支
      for k,v in projectMap.items():
        create_branch(sourceBranchName, newBranchName, k, v)
        print('工程【{}】基于分支【{}】创建分支【{}】成功'.format(k.name, sourceBranchName, newBranchName))
    else:
      print('ERROR: 请在path.yaml文件配置各工程路径！！！')
      sys.exit(1)
    