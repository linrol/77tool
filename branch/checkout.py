# coding=utf-8

import utils
import sys
import closeGit
from concurrent.futures import ThreadPoolExecutor, as_completed

class Checout:
  def __init__(self, branchName, close=False):
    self.branchName = branchName
    self.close = close
    self.pool = ThreadPoolExecutor(max_workers=10)

  # 执行器
  def execute(self):
    projectInfoMap = utils.project_path()
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
    branch = projectInfo.getBranch(self.branchName)
    if branch is None:
      return None
    else:
      projectInfo.checkout(branchName)
      print('工程【{}】检出分支【{}】成功'.format(projectInfo.getName(), branchName))
      return projectInfo

#检出指定分支，支持设置git分支管理
#python3 checkout.py hotfix true
if __name__ == "__main__":

  branchName=''
  close = False # 是否需要关闭git管理
  if len(sys.argv) == 2 :
    branchName=sys.argv[1]
  elif len(sys.argv) == 3 :
    branchName=sys.argv[1]
    close = (sys.argv[2].lower() == 'true')
  else:
    print ("ERROR: 输入参数错误, 正确的参数为：<branch> [<closeGit>]")
    sys.exit(1)

  executor = Checout(branchName, close)
  executor.execute()

