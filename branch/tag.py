# coding:utf-8
# 为指定分支创建tag
import os
import yaml
import sys
import utils
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"

class CreateTag:
  def __init__(self, branchName, releaseDate):
    self.branchName = branchName
    self.releaseDate= releaseDate
    self.pool = ThreadPoolExecutor(max_workers=10)

  def execute(self):
    projectInfoMap = utils.project_path()
    if len(projectInfoMap) > 0:
      self.projectVersionMap = self.get_project_version(projectInfoMap)
      #检查参数是否正确
      tasks = [self.pool.submit(self.checkAndCreate, projectInfo) for projectInfo in projectInfoMap.values()]
      wait(tasks, return_when=ALL_COMPLETED)
    else:
      print('WARNNING: 请在path.yaml文件配置各项目路径！！！')
      sys.exit(1)

  #获取各工程版本
  def get_project_version(self, projectInfoMap):
    buildName = 'build'
    if buildName in list(projectInfoMap.keys()):
      buildInfo = projectInfoMap[buildName]
      buildPath = buildInfo.getPath()
      buildBranch = buildInfo.getBranch(self.branchName)
      if buildBranch is None:
        print('ERROR: 工程【build】不存在分支【{}】'.format(self.branchName))
        sys.exit(1)
      else:
        if not buildInfo.checkout(self.branchName):
          print('ERROR: 工程【build】检出分支【{}】失败'.format(self.branchName))
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
  def checkAndCreate(self, projectInfo):
    branch = projectInfo.getBranch(self.branchName)
    #有指定分支的项目切换到指定分支
    if (branch is None):
      return None
    else:
      if projectInfo.checkout(self.branchName):
        projectName = projectInfo.getName()
        if projectName == 'build':
          tagName = '{}-{}'.format(self.releaseDate, self.branchName)
        elif projectInfo.getModule() == 'platform':
          version = self.projectVersionMap.get('framework', None)
          if self.check_tag_exist(projectInfo) or version is None or len(version) == 0:
            return None
          tagName = '{}-{}'.format(version, self.branchName)
        else:
          version = self.projectVersionMap.get(projectName, None)
          if version is None or len(version) == 0:
            return None
          tagName = '{}-{}'.format(version, self.branchName)
        if projectInfo.getTag(tagName) is None:
          projectInfo.createTag(tagName, self.branchName)
          print('工程【{}】分支【{}】打Tag【{}】成功'.format(projectName, self.branchName, tagName))

  #工程分支最新提交上面是否有这个分支的tag，如果有，则不需要再打tag（主要用于framework下的工程检查是否需要打tag）
  def check_tag_exist(self, projectInfo):
    commits = projectInfo.getProject().commits.list(ref_name=self.branchName)
    commit = commits[0]
    tagMaps = commit.refs('tag')
    if tagMaps is not None and len(tagMaps)>0:
      for tagMap in tagMaps:
        existTagName = tagMap.get('name', None)
        if existTagName is not None and existTagName.endswith(self.branchName):
          return True
    return False

#打tag
#python3 tag.py hotfix 20210102
if __name__ == "__main__":
  if len(sys.argv) == 3 :
    branchName=sys.argv[1]
    releaseDate=sys.argv[2]
  else:
    print ("ERROR: 输入参数错误, 正确的参数为：<branch> <release date>")
    sys.exit(1)

  executor = CreateTag(branchName, releaseDate)
  executor.execute()