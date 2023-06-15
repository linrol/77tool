# coding=utf-8
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED
import utils

class CheckResult():
  def __init__(self, projectInfo, skip, message=None, remark=None):
    self.__projectInfo = projectInfo
    self.__skip = skip# 是否忽略，不进行删除
    self.__message = message
    self.__remark = remark

  def getProjectInfo(self):
    return self.__projectInfo
  #是否跳过不删除分支
  def skip(self):
    return self.__skip
  # 是否检查通过，允许删除分支
  def isDelete(self):
    return (not self.__skip) and (self.__message is None or len(self.__message) == 0)
  #错误信息
  def getMessage(self):
    return self.__message
  #备注信息
  def getRemark(self):
    return self.__remark

class DeleteBranch:
  def __init__(self, deleteBranchName, mergedBranchName, projectNames=None, mergeError = True):
    self.deleteBranchName = deleteBranchName
    if mergedBranchName.lower() == 'none':
      self.mergedBranchName = None
    else:
      self.mergedBranchName = mergedBranchName
    self.projectNames = projectNames
    self.mergeError = mergeError # merge错误检查（false:删除已经merge的工程分支，没有merge则不删除；true:只要有一个工程的分支没有merge则所有工程不进行删除）
    #参数检查
    self.check_param()

    self.pool = ThreadPoolExecutor(max_workers=10)

  def check_param(self):
    if(self.deleteBranchName == 'master' or self.deleteBranchName == 'stage'):
      print('ERROR: 【{}】分支不允许删除！！！！！！！！！！！'.format(self.deleteBranchName))
      sys.exit(1)


  def execute(self):
    #获取要操作的工程信息
    projectInfoMap = utils.init_projects(self.projectNames)

    if len(projectInfoMap) > 0:
      #获取需要进行分支删除的工程（key:gitlab的project对象，value:本地工程路径）
      deletes = self.get_delete_project(projectInfoMap)
      if len(deletes) > 0:
        #删除工程分支
        tasks = [self.pool.submit(self.delete_branch, projectInfo) for projectInfo in deletes]
        wait(tasks, return_when=ALL_COMPLETED)
      else:
        print("所有工程均不存在分支【{}】".format(self.deleteBranchName))
    else:
      print('没有要操作工程')
      sys.exit(1)

  #获取有来源分支，并且已经合并至目标分支的工程（返回：key:gitlab的project对象，value:本地工程路径）
  def get_delete_project(self, projectInfoMap):
    error=[]
    deletes=[]
    tasks = [self.pool.submit(self.check_delete, projectInfo) for projectInfo in projectInfoMap.values()]
    for future in as_completed(tasks):
      result = future.result()
      if result.isDelete():
        deletes.append(result.getProjectInfo())
      elif not result.skip():
        # 检查不通过
        error.append(result.getMessage())

    if len(error) > 0:
      #如果有错误信息则不执行删除
      utils.print_list("ERROR: ", error)
      sys.exit(1)
    else:
      return deletes

  #检查工程分支是否能删除
  def check_delete(self, projectInfo):
    project = projectInfo.getProject()
    projectName = projectInfo.getName()
    if project is None :
      return CheckResult(projectInfo, skip=False, message='工程【{}】不存在'.format(projectName))
    else:
      sourceBranch = projectInfo.getBranch(self.deleteBranchName)
      #有待删除分支的项目才删除改项目的分支
      if (sourceBranch is None):
        return CheckResult(projectInfo, skip=True, remark='没有待删除的分支')
      else:
        # projectPath = projectInfo.getPath()
        if self.mergedBranchName is None:
          #未指定检查分支，则不检查是否已合并
          return CheckResult(projectInfo, skip=False, remark='不检查是否合并')
        else:
          targetBranch = projectInfo.getBranch(self.mergedBranchName)
          if (targetBranch is None):
            return CheckResult(projectInfo, skip=False, message='工程【{}】目标分支【{}】不存在'.format(projectName, self.mergedBranchName))
          else:
            # isMerge = utils.check_branch_merge(projectName, projectPath, deleteBranchName, mergedBranchName)
            isMerge = projectInfo.checkMerge(self.deleteBranchName, self.mergedBranchName)
            if isMerge:
              return CheckResult(projectInfo, skip=False)
            else:
              if self.mergeError:
                message = '工程【{}】分支【{}】未合并至目标分支【{}】,不能删除分支【{}】'.format(projectName,
                                                                 self.deleteBranchName,
                                                                 self.mergedBranchName,
                                                                 self.deleteBranchName)
                return CheckResult(projectInfo, skip=False, message=message)
              else:
                remark = 'WARNNING：工程【{}】分支【{}】未合并至目标分支【{}】！！！'.format(projectName, self.deleteBranchName, self.mergedBranchName)
                return CheckResult(projectInfo, skip=True, remark=remark)


  #检查指定分支是否合并至master，已合并则删除
  #path:build工程路径
  def delete_branch(self, projectInfo):
    projectInfo.deleteLocalBranch(self.deleteBranchName, self.mergedBranchName)
    projectInfo.deleteRemoteBranch(self.deleteBranchName)
    if self.mergedBranchName is None:
      print('工程【{}】删除分支【{}】成功'.format(projectInfo.getName(), self.deleteBranchName))
    else:
      print('工程【{}】删除分支【{}】成功，该分支已合并至分支【{}】'.format(projectInfo.getName(), self.deleteBranchName, self.mergedBranchName))




#校验分支是否合并至指定分支(默认master)，若已合并则删除该分支
#python3 checkanddeleted.py hotfix
if __name__ == "__main__":
  #参数解析
  deleteBranchName = ''
  mergedBranchName = ''
  projectNames = []
  if len(sys.argv) < 3 :
    print ("ERROR: 输入参数错误, 正确的参数为：<delete branch> <merged branch> [<projectName>...]")
    sys.exit(1)
  else:
    deleteBranchName = sys.argv[1]
    mergeError = True#merge错误检查（false:删除已经merge的工程分支，没有merge则不删除；true:只要有一个工程的分支没有merge则所有工程不进行删除）
    mergedBranchName = sys.argv[2]
    infos=mergedBranchName.split('.')
    if len(infos) > 1:
      mergedBranchName = infos[0]
      mergeError = (infos[1].lower() != 'false')

    if len(sys.argv) > 3:
      projectNames = sys.argv[3:]

  executor = DeleteBranch(deleteBranchName, mergedBranchName, projectNames, mergeError)
  executor.execute()