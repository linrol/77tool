# coding=utf-8
import sys
import gitlab
import utils


#检查参数是否正确（返回：key:gitlab的project对象，value:本地工程信息）
def check_project(branchName, projectNames, projectInfoMap):
  projectMap={}
  for projectName in projectNames:
    project = utils.get_project(projectName)
    if project is None :
      continue
    else:
      sourceBranch = utils.check_branch_exist(project, branchName)
      #分支存在的才进行权限修改
      if (sourceBranch is None):
        continue
      else:
        projectMap[project] = projectInfoMap[projectName]
  if len(projectMap) == 0:
    print("[ERROR]工程分支[{}]不存在： ".format(branchName))
    print(projectNames)
    sys.exit(1)
  else:
    return projectMap

#设置分支保护
def protect_branch(branchName, project,access):
  projectName = project.name
  utils.delete_branch_protect(project, branchName)
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
    print('【{}】【{}】分支保护删除成功'.format(project.name, branchName))
    return

  p_branch = project.protectedbranches.create({
      'name': branchName,
      'merge_access_level': mergeAccessLevel,
      'push_access_level': pushAccessLevel
  })
  print('【{}】【{}】分支保护成功'.format(project.name, p_branch.name))



#工程分支设置保护 默认保护指定分支的所有工程
#例：保护分支ztb-test 权限为hotfix
#python3 protectBranch.py ztb-test hotfix fiance build init-data
if __name__ == "__main__":
  if len(sys.argv) < 3 :
    print ("ERROR: 输入参数错误, 正确的参数为： <branch> <access> [<projectName>...]")
    sys.exit(1)
  else:
    #获取所有工程的本地路径
    projectInfoMap = utils.project_path()
    projectNames =[]
    if len(sys.argv) > 3:
      projectNames = sys.argv[3:]
    else:
      projectNames = list(projectInfoMap.keys())
    branchName = sys.argv[1]
    access = sys.argv[2]

    if len(projectInfoMap) > 0:
      #检查参数是否正确
      projectMap = check_project(branchName, projectNames, projectInfoMap)
      #保护分支
      for k,v in projectMap.items():
        protect_branch(branchName, k, access)
        # print('工程【{}】分支【{}】保护成功【{}】'.format(k.name, branchName, access))
    else:
      print('ERROR: 请在path.yaml文件配置各项目路径！！！')
      sys.exit(1)
    