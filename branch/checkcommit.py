# coding:utf-8
# 检查所有项目指定分支的合并情况
import datetime
import os
import time
import sys
import utils

# 获取提交记录映射（key:作者邮箱+创作时间   value:commit对象）
def get_commit_map(project, branchName, since):
  commitMap={}
  branch = utils.check_branch_exist(project, branchName)
  if branch is None :
    print("ERROR:工程【{}】分支【{}】不存在！！！".format(project.name, branchName))
    return commitMap

  print("获取工程【{}】分支【{}】提交记录【{}】".format(project.name, branchName, since))
  commits = project.commits.list(all=True, query_parameters={'ref_name': branchName,'since':since})
  for commit in commits:
    if check_commit(project.name, commit):
      key = commit.author_email + commit.authored_date
      commitMap[key] = commit
  return commitMap


# 检查commit是否需要进行合并
def check_commit(projectName, commit):
  # 1.mr会有一个合并记录,不进行合并
  if len(commit.parent_ids) > 1:
    return False
  # 2.曾天保提交的前端UiConfig预制数据不进行合并
  if projectName=='init-data' and commit.title.startswith('<数据预制>前端UiConfig数据预置') and commit.author_email=='tianbao.zeng@q7link.com':
    return False
  # 2.曾天保提交的版本修改不进行合并
  if commit.title.startswith('<版本修改>'):
    return False
  # 3.运维开发账号提交数据不进行合并
  if commit.author_email=='devops@q7link.com':
    return False
  # 4.版本修改不需要进行合并
  diffs = commit.diff()
  isPom = True
  for diff in diffs:
    if not diff['new_path'].endswith('pom.xml'):
      if not diff['new_path'].endswith('dump.xml'):
        if not diff['new_path'].endswith('dump4unpack.xml'):
          isPom = False
  if isPom and commit.title.find('版本') != -1:
    return False

  return True


#获取需要执行的项目（即有来源分支的工程）
def get_project(branchName, projectNames):
  projects =[]
  for projectName in projectNames:
    project = utils.get_project(projectName)
    if project is None :
      # print('工程【{}】不存在'.format(projectName))
      continue
    else:
      branch = utils.check_branch_exist(project, branchName)
      if (branch is None):
        # print("WARNNING:工程【{}】分支【{}】不存在！！！".format(project.name, branchName))
        continue
      else:
        projects.append(project)

  return projects


# 检查所有项目指定分支的合并情况（默认检查十天内的提交）
# 例：检查hotfix分支的提交是否合并至dev分支
#python3 checkcommit.py hotfix dev
# if __name__ == "__main__":
  projectNames = ['framework', 'baseapp', 'init-data', 'project', 'finance', 'procdesign', 'basebi', 'graphql', 'identity', 'reconcile']
  sourceBranchName = ''
  targetBranchName = ''
  offset = 10
  if len(sys.argv) == 3:
    sourceBranchName = sys.argv[1]
    targetBranchName = sys.argv[2]
  elif len(sys.argv) == 4:
    sourceBranchName = sys.argv[1]
    targetBranchName = sys.argv[2]
    offset = sys.argv[3]
  else:
    print ("ERROR: 输入参数错误, 正确的参数为：<source branch> <target branch> [<time offset>]")
    sys.exit(1)

  projects = get_project(sourceBranchName, projectNames)
  result = []
  allMerge = True

  now = datetime.datetime.now();
  since = (now - datetime.timedelta(days=abs(int(offset)))).strftime("%Y-%m-%dT00:00:00Z")

  for project in projects:
    sourceMap = get_commit_map(project, sourceBranchName, since)
    targetMap = get_commit_map(project, targetBranchName, since)
    if targetMap == None:
      #找不到目标分支时，才会返回None，找不到目标分支则不进行处理
      continue
    noCommitKeys = list(sourceMap.keys()) - list(targetMap.keys())
    if len(noCommitKeys) == 0:
      # 没有差异则不记录
      continue
    result.append("********************************************************************************************************************************************\n")
    result.append("********************************************************************************************************************************************\n")
    result.append("********************project[{}] from branch[{}] to branch[{}]  startDate[{}]********************\n".format(project.name, sourceBranchName, targetBranchName, since))
    result.append("********************************************************************************************************************************************\n")
    result.append("********************************************************************************************************************************************\n")
    for i,noCommitKey in enumerate(noCommitKeys):
      allMerge = False
      commit = sourceMap[noCommitKey]
      result.append("{}.id[{}]  user[{}]  email[{}]  time[{}]\n".format(i+1, commit.id, commit.committer_name, commit.committer_email, commit.authored_date))
      result.append(commit.message)
      result.append("\n\n")

  if allMerge:
    print("分支[{}]已全部合并至分支[{}]".format(sourceBranchName, targetBranchName))
    sys.exit(0)

  # 创建文件夹
  path = "./log/noMerge/"
  if not os.path.exists(path):
    os.makedirs(path, 0o777)

  # 创建文件并保存比较结果内容
  fileName = "{}_to_{}-{}.txt".format(sourceBranchName,targetBranchName, time.strftime("%Y%m%d%H%M%S",time.localtime()))
  filePath = os.path.join(path, fileName)
  with open(filePath,mode='a+',encoding='utf-8') as file:
    file.writelines(result)
  print("执行成功【{}】".format(fileName))


