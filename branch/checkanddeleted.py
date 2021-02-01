# coding=utf-8
import sys
import subprocess
import utils


#获取有来源分支，并且已经合并至目标分支的工程（返回：key:gitlab的project对象，value:本地工程路径）
def get_delete_project(projectInfoMap, sourceBranchName, targetBranchName, mergeError):
  error=[]
  deletes=[]
  for projectName,projectInfo in projectInfoMap.items():
    if projectInfo is None:
      continue

    project = projectInfo.getProject()
    if project is None :
      error.append('工程【{}】不存在'.format(projectName))
    else:
      sourceBranch = projectInfo.getBranch(sourceBranchName)
      #有来源分支的项目才删除改项目的来源分支
      if (sourceBranch is None):
        continue
      else:
        # projectPath = projectInfo.getPath()
        if targetBranchName is None:
          #未指定检查分支，则不检查是否已合并
          deletes.append(projectInfo)
        else:
          targetBranch = projectInfo.getBranch(targetBranchName)
          if (targetBranch is None):
            error.append('工程【{}】目标分支【{}】不存在'.format(projectName, targetBranchName))
          else:
            # isMerge = utils.check_branch_merge(projectName, projectPath, sourceBranchName, targetBranchName)
            isMerge = projectInfo.checkMerge(sourceBranchName, targetBranchName)
            if isMerge:
              deletes.append(projectInfo)
            else:
              if mergeError:
                error.append('工程【{}】分支【{}】未合并至目标分支【{}】,不能删除分支【{}】'.format(projectName, sourceBranchName, targetBranchName, sourceBranchName))
              else:
                print('WARNING：工程【{}】分支【{}】未合并至目标分支【{}】！！！'.format(projectName, sourceBranchName, targetBranchName))
              continue
  if len(error) > 0:
    #如果有错误信息则不执行删除
    utils.print_list("ERROR: ", error)
    sys.exit(1)
  else:
    return deletes


#检查指定分支是否合并至master，已合并则删除
#path:build工程路径
def delete_branch(deletes, sourceBranchName, targetBranchName):
  for projectInfo in deletes:
    projectInfo.deleteLocalBranch(sourceBranchName, targetBranchName)
    projectInfo.deleteRemoteBranch(sourceBranchName)
    if targetBranchName is None:
      print('工程【{}】删除分支【{}】成功'.format(projectInfo.getName(), sourceBranchName))
    else:
      print('工程【{}】删除分支【{}】成功，该分支已合并至分支【{}】'.format(projectInfo.getName(), sourceBranchName, targetBranchName))




#校验分支是否合并至指定分支(默认master)，若已合并则删除该分支
#python3 checkanddeleted.py hotfix
if __name__ == "__main__":
  #参数解析
  sourceBranchName = ''
  targetBranchName = ''
  projectNames = []
  if len(sys.argv) < 3 :
    print ("ERROR: 输入参数错误, 正确的参数为：<source branch> <target branch> [<projectName>...]")
    sys.exit(1)
  else:
    sourceBranchName = sys.argv[1]
    mergeError = True#merge错误检查（false:删除已经merge的工程分支，没有merge则不删除；true:只要有一个工程的分支没有merge则所有工程不进行删除）
    if sys.argv[2].lower() == 'none':
      targetBranchName = None
    else:
      targetBranchName = sys.argv[2]

      infos=targetBranchName.split('.')
      if len(infos) > 1:
        targetBranchName = infos[0]
        mergeError = (infos[1].lower() != 'false')

    if len(sys.argv) > 3:
      projectNames = sys.argv[3:]

  if(sourceBranchName == 'master' or sourceBranchName == 'stage'):
    print('ERROR: 【{}】分支不允许删除！！！！！！！！！！！'.format(sourceBranchName))
    sys.exit(1)

  #获取要操作的工程信息
  projectInfoMap = utils.project_path(projectNames)

  if len(projectInfoMap) > 0:
    #获取需要进行分支删除的工程（key:gitlab的project对象，value:本地工程路径）
    deletes = get_delete_project(projectInfoMap, sourceBranchName, targetBranchName, mergeError)
    if len(deletes) > 0:
      #删除工程分支
      delete_branch(deletes, sourceBranchName, targetBranchName)
    else:
      print("所有工程均不存在分支【{}】".format(sourceBranchName))
  else:
    print('没有要操作工程')
    sys.exit(1)
