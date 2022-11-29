# coding=utf-8
import sys
import utils
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

class ProjectBranch:
  def __init__(self, branchName, access, projectNames=None):
    self.branchName = branchName
    self.projectNames = projectNames
    self.access = access
    # 检查入参
    self.check_param()

    self.pool = ThreadPoolExecutor(max_workers=10)

  def check_param(self):
    if self.branchName in ['master', 'stage'] and self.access in ('d','delete') :
      print('ERROR: 【{}】分支的分支保护不允许删除！！！！！！！！！！！'.format(self.branchName))
      sys.exit(1)

  def execute(self):
    projectInfoMap = utils.project_path(self.projectNames)
    if len(projectInfoMap) > 0:
      #检查参数是否正确
      tasks = [self.pool.submit(self.checkAndProtect, projectInfo) for projectInfo in projectInfoMap.values()]
      wait(tasks, return_when=ALL_COMPLETED)
    else:
      print('ERROR: 请在path.yaml文件配置各项目路径！！！')
      sys.exit(1)


  #检查参数是否正确（返回：工程信息）
  def checkAndProtect(self, projectInfo):
    branch = projectInfo.getBranch(self.branchName)
    #分支存在的才进行权限修改
    if (branch is None):
      return None
    else:
      self.protectBranch(projectInfo)
      return projectInfo

  #设置分支保护
  def protectBranch(self, projectInfo):
    projectName = projectInfo.getName()
    mergeAccessLevel = utils.DEVELOPER_ACCESS
    pushAccessLevel = utils.DEVELOPER_ACCESS
    #release分支设置管理员全权限，hotfix设置管理员merge权限。build和init-data设置管理员全权限
    if self.access == 'release':
      mergeAccessLevel = utils.MAINTAINER_ACCESS
      pushAccessLevel = utils.MAINTAINER_ACCESS
    elif self.access == 'hotfix' or self.access == 'emergency':
      if projectName == 'build' or projectName == 'init-data':
        mergeAccessLevel = utils.MAINTAINER_ACCESS
        pushAccessLevel = utils.MAINTAINER_ACCESS
      else:
        mergeAccessLevel = utils.MAINTAINER_ACCESS
        pushAccessLevel = utils.VISIBILITY_PRIVATE
    elif self.access == 'none':
      mergeAccessLevel = utils.VISIBILITY_PRIVATE
      pushAccessLevel = utils.VISIBILITY_PRIVATE
    elif self.access == 'd' or self.access =='delete':
      projectInfo.deleteBranchProtect(self.branchName)
      print('【{}】【{}】分支保护删除成功'.format(projectName, self.branchName))
      return

    _, mergeRole, pushRole = projectInfo.protectBranch(self.branchName, mergeAccessLevel, pushAccessLevel)
    print('工程【{}】分支【{}】保护成功，允许【{}】合并,【{}】推送'.format(projectName, self.branchName, mergeRole, pushRole))



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

  executor = ProjectBranch(branchName, access, projectNames)
  executor.execute()