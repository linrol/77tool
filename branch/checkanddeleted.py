# coding=utf-8
import sys
import subprocess
import utils


#获取有来源分支，并且已经合并至目标分支的工程（返回：key:gitlab的project对象，value:本地工程路径）
def get_delete_project(projectPaths, sourceBranchName, targetBranchName):
  error=[]
  deletes={}
  for k,v in projectPaths.items():
    project = utils.get_project(k)
    if project is None :
      error.append('工程【{}】不存在'.format(k))
    else:
      sourceBranch = utils.check_branch_exist(project, sourceBranchName)
      #有来源分支的项目才删除改项目的来源分支
      if (sourceBranch is None):
        continue
      else:
        targetBranch = utils.check_branch_exist(project, targetBranchName)
        if (targetBranch is None):
          error.append('工程【{}】目标分支【{}】不存在'.format(k, targetBranchName))
        else:
          isMerge = utils.check_branch_merge(k, v, sourceBranchName, targetBranchName)
          if isMerge:
            deletes[project] = v
          else:
            error.append('工程【{}】分支【{}】未合并至目标分支【{}】,不能删除分支【{}】'.format(k, sourceBranchName, targetBranchName, sourceBranchName))
            continue
  if len(error) > 0:
    #如果有错误信息则不执行删除
    utils.print_list("ERROR: ", error)
    sys.exit(1)
  else:
    return deletes


#检查指定分支是否合并至master，已合并则删除
#path:build工程路径
def delete_branch(deletes, projectPaths, sourceBranchName, targetBranchName):
  for k,v in deletes.items():
    projectName = k.name
    path = projectPaths[projectName]
    subprocess.getstatusoutput('cd ' + path +';git checkout ' + targetBranchName)
    subprocess.getstatusoutput('cd ' + path +';git pull')
    #删除本地分支(使用-d，如果没有合并到当前分支，删除会报错)
    [result, msg] = subprocess.getstatusoutput('cd ' + path +';git branch -d ' + sourceBranchName)
    if result==0:
      #删除远程分支
      delete_origin_branch(k, sourceBranchName)
      subprocess.getstatusoutput('cd ' + path +';git fetch -p')
      print('工程【{}】删除分支【{}】成功，该分支已合并至分支【{}】'.format(k.name, sourceBranchName, targetBranchName))
    else:
      print('ERROR: 工程【{}】删除本地分支【{}】,报错！！！'.format(projectName, sourceBranchName))

#删除远程分支
def delete_origin_branch(project, branchName):
  if(branchName == 'master' or branchName == 'dev'):
    print('ERROR: 【{}】分支不允许删除！！！！！！！！！！！'.format(branchName))
  #删除分支保护
  utils.delete_branch_protect(project, branchName)
  #删除分支
  project.branches.delete(branchName)



#校验分支是否合并至指定分支(默认master)，若已合并则删除该分支
#python3 checkanddeleted.py hotfix
if __name__ == "__main__":
  #参数解析
  sourceBranchName = ''
  targetBranchName = 'master'
  if len(sys.argv) == 2 :
    sourceBranchName = sys.argv[1]
  elif len(sys.argv) == 3 :
    sourceBranchName = sys.argv[1]
    targetBranchName = sys.argv[2]
  else:
    print ("ERROR: 输入参数错误, 正确的参数为：<source branch> [<target branch>(默认master)]")
    sys.exit(1)
  if(sourceBranchName == 'master' or sourceBranchName == 'dev'):
    print('ERROR: 【{}】分支不允许删除！！！！！！！！！！！'.format(sourceBranchName))

  #获取所有工程的本地路径
  projectPaths = utils.project_path()
  if len(projectPaths) > 0:
    #获取需要进行分支删除的工程（key:gitlab的project对象，value:本地工程路径）
    deletes = get_delete_project(projectPaths, sourceBranchName, targetBranchName)    
    if len(deletes) > 0:
      #删除工程分支
      delete_branch(deletes, projectPaths, sourceBranchName, targetBranchName)
    else:
      print("所有工程均不存在分支【{}】".format(sourceBranchName))
  else:
    print('ERROR: 请在path.yaml文件配置各项目路径！！！')
    sys.exit(1)
