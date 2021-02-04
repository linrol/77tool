# coding=utf-8

import utils
import sys
import closeGit

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


  projectInfoMap = utils.project_path()
  if len(projectInfoMap) == 0:
    sys.exit(1)

  projectMap = {}

  for projectName,projectInfo in projectInfoMap.items():
    branch = projectInfo.getBranch(branchName)
    if branch is None:
      continue
    else:
      projectInfo.checkout(branchName)
      projectMap[projectName] = projectInfo
      print('工程【{}】检出分支【{}】成功'.format(projectName, branchName))

  if close:
    closeGit.close_git(projectMap)
