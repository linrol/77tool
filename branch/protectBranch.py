# coding=utf-8
import sys
import gitlab
import utils


#检查参数是否正确（返回：工程信息集合）
def check_project(projectInfoMap, branchName):
  protects=[]
  for projectName, projectInfo in projectInfoMap.items():
    project = projectInfo.getProject()
    branch = projectInfo.getBranch(branchName)
    #分支存在的才进行权限修改
    if (branch is None):
      continue
    else:
      protects.append(projectInfo)
  if len(protects) == 0:
    print("[ERROR]工程分支[{}]不存在： ".format(branchName))
    print(list(projectInfoMap.keys()))
    sys.exit(1)
  else:
    return protects

#设置分支保护
def protect_branch(projectInfo, branchName,access):
  projectName = projectInfo.getName()
  mergeAccessLevel = gitlab.DEVELOPER_ACCESS
  pushAccessLevel = gitlab.DEVELOPER_ACCESS
  #release分支设置管理员全权限，hotfix设置管理员merge权限。build和init-data设置管理员全权限
  if access == 'release':
    mergeAccessLevel = gitlab.MAINTAINER_ACCESS
    pushAccessLevel = gitlab.MAINTAINER_ACCESS
  elif access == 'hotfix' or access == 'emergency':
    if projectName == 'build' or projectName == 'init-data':
      mergeAccessLevel = gitlab.MAINTAINER_ACCESS
      pushAccessLevel = gitlab.MAINTAINER_ACCESS
    else:
      mergeAccessLevel = gitlab.MAINTAINER_ACCESS
      pushAccessLevel = gitlab.VISIBILITY_PRIVATE
  elif access == 'none':
      mergeAccessLevel = gitlab.VISIBILITY_PRIVATE
      pushAccessLevel = gitlab.VISIBILITY_PRIVATE
  elif access == 'd' or access =='delete':
    projectInfo.deleteBranchProtect(branchName)
    print('【{}】【{}】分支保护删除成功'.format(projectName, branchName))
    return

  projectInfo.protectBranch(branchName, mergeAccessLevel, pushAccessLevel)
  print('工程【{}】分支【{}】保护成功'.format(projectName, branchName))



#工程分支设置保护 默认保护指定分支的所有工程
#例：保护分支ztb-test 权限为hotfix
#python3 protectBranch.py ztb-test hotfix fiance build init-data
if __name__ == "__main__":
  if len(sys.argv) < 3 :
    print ("ERROR: 输入参数错误, 正确的参数为： <branch> <access> [<projectName>...]")
    sys.exit(1)
  else:
    projectNames =[]
    if len(sys.argv) > 3:
      projectNames = sys.argv[3:]
    branchName = sys.argv[1]
    access = sys.argv[2]

    #获取所有工程的本地路径
    projectInfoMap = utils.project_path(projectNames)
    if len(projectInfoMap) > 0:
      #检查参数是否正确
      protects = check_project(projectInfoMap, branchName)
      #保护分支
      for projectInfo in protects:
        protect_branch(projectInfo, branchName, access)
        # print('工程【{}】分支【{}】保护成功【{}】'.format(k.name, branchName, access))
    else:
      print('ERROR: 请在path.yaml文件配置各项目路径！！！')
      sys.exit(1)
    