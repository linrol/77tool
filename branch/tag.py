# coding:utf-8
# 为指定分支创建tag
import os
import yaml
import sys
import traceback
import utils
import subprocess
import xml.etree.ElementTree as ET

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"

#获取各工程版本
def get_project_version(branchName, projectInfoMap):
  buildName = 'build'
  if buildName in commits(projectInfoMap.keys()):
    buildInfo = projectInfoMap[buildName]
    buildPath = buildInfo.getPath()
    buildBranch = buildInfo.getBranch(branchName)
    if buildBranch is None:
      print('ERROR: 工程【build】不存在分支【{}】'.format(branchName))
      sys.exit(1)
    else:
      if not buildInfo.checkout(branchName):
        print('ERROR: 工程【build】检出分支【{}】失败'.format(branchName))
        sys.exit(1)
      else:
        # 获取config.yaml
        filename = os.path.join(os.curdir, buildPath + '/config.yaml').replace("\\", "/")
        f = open(filename)
        config = yaml.load(f, Loader=yaml.FullLoader)

        projectVersionMap={}
        for item in config.values():
          for k,v in item.items():
            projectVersionMap[k] = v
        return projectVersionMap
  else:
    print('ERROR: 请在path.yaml文件中指定build工程的路径')
    sys.exit(1)

#获取需要执行的项目，并检出其指定分支
def get_project(branchName, projectInfoMap):
  changes =[]
  for projectName,projectInfo in projectInfoMap.items():
    branch = projectInfo.getBranch(branchName)
    #有指定分支的项目切换到指定分支
    if (branch is None):
      continue
    else:
      if projectInfo.checkout(branchName):
        changes.append(projectInfo)
  return changes

#工程分支最新提交上面是否有这个分支的tag，如果有，则不需要再打tag（主要用于framework下的工程检查是否需要打tag）
def check_tag_exist(branchName, projectInfo):
  commits = projectInfo.getProject().commits.list(ref_name=branchName)
  commit = commits[0]
  tagMaps = commit.refs('tag')
  if tagMaps is not None and len(tagMaps)>0:
    for tagMap in tagMaps:
      existTagName = tagMap.get('name', None)
      if existTagName is not None and existTagName.endswith(branchName):
        return True
  return False

#打tag
#python3 tag.py hotfix 20210102
if __name__ == "__main__":
  if len(sys.argv) == 3 :
    branchName=sys.argv[1]
    releaseDate=sys.argv[1]
  else:
    print ("ERROR: 输入参数错误, 正确的参数为：<branch> <release date>")
    sys.exit(1)

  #获取所有工程的本地路径
  projectInfoMap = utils.project_path()
  if len(projectInfoMap) > 0:
    changes = get_project(branchName, projectInfoMap)
    projectVersionMap = get_project_version(branchName, projectInfoMap)

    for projectInfo in changes:
      projectName = projectInfo.getName()
      if projectName == 'build':
        tagName = '{}-{}'.format(releaseDate, branchName)
      elif projectInfo.getModule() == 'platform':
        version = projectInfoMap.get('framework', None)
        if check_tag_exist(branchName, projectInfo) or version is None or len(version) == 0:
          continue
        tagName = '{}-{}'.format(version, branchName)
      else:
        version = projectInfoMap.get(projectName, None)
        if version is None or len(version) == 0:
          continue
        tagName = '{}-{}'.format(version, branchName)
      if projectInfo.getTag(tagName) is None:
        projectInfo.createTag(tagName, branchName)
        print('工程【{}】分支【{}】打Tag【{}】成功'.format(projectName, branchName, tagName))
  else:
    print('ERROR: 请在path.yaml文件配置各项目路径！！！')
    sys.exit(1)