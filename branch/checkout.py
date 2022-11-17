# coding=utf-8

import utils
import sys
import closeGit
from concurrent.futures import ThreadPoolExecutor, as_completed

class Checout:
  def __init__(self, branches, module=None, close=False, intersection=False):
    self.branches = branches
    self.branchNames = ".".join(branches)
    self.module = module
    self.is_front = module in ["front"]
    self.close = close
    self.intersection = intersection
    self.pool = ThreadPoolExecutor(max_workers=10)

  # 执行器
  def execute(self):
    if self.is_front:
      projectInfoMap = utils.project_path(self.module)
    else:
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
    if self.intersection and not projectInfo.branchIntersection(self.branches):
        return None
    branch = projectInfo.getBranch(self.branchNames)
    if branch is not None:
      projectInfo.checkout(branch.name)
      print('工程【{}】检出分支【{}】成功'.format(projectInfo.getName(), branch.name))
      return projectInfo
    return None

#检出指定分支，支持设置git分支管理
#python3 checkout.py hotfix true
if __name__ == "__main__":
  if len(sys.argv) < 2:
    print ("ERROR: 输入参数错误, 正确的参数为：[module] <branch> [<closeGit>]")
    sys.exit(1)
  branchNames=sys.argv[1:]
  module = 'backend'
  close = False #是否需要关闭git管理
  if sys.argv[1] in ["backend", "front"]:
    module = sys.argv[1]
    branchNames.remove(module)
  if sys.argv[-1].lower() in ["true", "false"]:
    close = (sys.argv[-1].lower() == 'true')
    branchNames.remove(sys.argv[-1])
  check_intersection = len(branchNames) > 1 #是否检出交集分支
  executor = Checout(branchNames, module, close, check_intersection)
  executor.execute()

