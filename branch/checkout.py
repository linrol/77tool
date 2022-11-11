# coding=utf-8

import utils
import sys
import closeGit
from concurrent.futures import ThreadPoolExecutor, as_completed

class Checout:
  def __init__(self, branchNames, projectNames, close=False):
    self.branchNames = branchNames
    self.projectNames = projectNames
    self.close = close
    self.pool = ThreadPoolExecutor(max_workers=10)

  # 执行器
  def execute(self):
    projectInfoMap = utils.project_path(self.projectNames)
    if len(projectInfoMap) == 0:
      sys.exit(1)

    projectMap = {}

    tasks = [self.pool.submit(self.checkoutBranch, projectInfo) for projectInfo in projectInfoMap.values()]
    for future in as_completed(tasks):
      result = future.result()
      if result is not None:
        projectMap[result.getName()] = result

    if close and len(projectMap) > 0:
      closeGit.close_git(projectMap)

  #检查是否有分支，如果有则检出分支
  def checkoutBranch(self, projectInfo):

    for branchName in self.branchNames.split("."):
      branch = projectInfo.getBranch(branchName)
      if branch is not None:
        projectInfo.checkout(branchName)
        print('工程【{}】检出分支【{}】成功'.format(projectInfo.getName(), branchName))
        return projectInfo
    return None

#检出指定分支，支持设置git分支管理
#python3 checkout.py hotfix true
if __name__ == "__main__":

  branchNames=''
  close = False # 是否需要关闭git管理
  projectNames = []
  if len(sys.argv) == 2 :
    branchNames=sys.argv[1]
  elif len(sys.argv) == 3 :
    branchNames=sys.argv[1]
    close = (sys.argv[2].lower() == 'true')
  elif len(sys.argv) > 3 :
    branchNames=sys.argv[1]
    close = (sys.argv[2].lower() == 'true')
    projectNames = sys.argv[3:]
  else:
    print ("ERROR: 输入参数错误, 正确的参数为：<branch> [<closeGit>]")
    sys.exit(1)

  executor = Checout(branchNames, projectNames, close)
  executor.execute()

