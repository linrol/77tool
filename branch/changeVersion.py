# coding:utf-8
# 修改所有项目依赖的framework版本
import os
import yaml
import sys
import traceback
import utils
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"

class ChangeVersion:
  def __init__(self, branchName,updateTest=False, needClear= False):
    self.branchName = branchName
    self.needClear= needClear#是否清空开发脚本，默认false(不清空)
    self.updateTest= updateTest#是否更新测试包版本，默认false(不更新)
    self.pool = ThreadPoolExecutor(max_workers=10)

  def execute(self):
    projectInfoMap = utils.project_path()
    if len(projectInfoMap) > 0:
      # 获取各工程版本
      projectVersionMap = self.get_project_version(projectInfoMap)

      # 获取需要修改的工程（即：有该分支的工程）
      changes = []
      tasks = [self.pool.submit(self.get_project, projectInfo) for projectInfo in projectInfoMap.values()]
      for future in as_completed(tasks):
        result = future.result()
        if result is not None:
          changes.append(result)

      #根据config.yaml修改拥有指定分支的工程依赖版本
      util = VersionUtils()
      for projectInfo in changes:
        util.update(projectInfo, projectVersionMap, changes, self.updateTest)

      #清空开发脚本及接口调用信息
      if self.needClear and ('build' in projectInfoMap):
        self.clear_script(projectInfoMap['build'].getPath())
        self.clear_interface(projectInfoMap['build'].getPath())
        print('工程【build】清空脚本完成')

    else:
      print('ERROR: 请在path.yaml文件配置各项目路径！！！')
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
          f = open(filename, encoding='utf-8')
          config = yaml.load(f, Loader=yaml.FullLoader)

          projectVersionMap={'baseapp-api':'${version.framework.baseapp-api}'}
          for item in config.values():
            if type(item) is dict:
              for k,v in item.items():
                projectVersionMap[k] = v
          return projectVersionMap
    else:
      print('ERROR: 请在path.yaml文件中指定build工程的路径')
      sys.exit(1)


  #获取需要执行的项目，并检出其指定分支
  def get_project(self, projectInfo):
    branch = projectInfo.getBranch(self.branchName)
    #有指定分支的项目切换到指定分支
    if (branch is None):
      return None
    else:
      if projectInfo.checkout(self.branchName):
        return projectInfo
      else:
        return None

  #清空开发脚本
  def clear_script(self, buildPath):
    childPaths = ['1_before', '2_after', 'recovery']
    for itemPath in childPaths:
      filePath = buildPath + "/upgrade/" + itemPath
      fileNames = os.listdir(filePath)
      for filename in fileNames:
        if (filename.lower().find('identity') != -1) or (filename.lower().find('reconcile') != -1) or (filename.lower().find('tenantallin') != -1) :
          #清空文件内容
          self.clearFile(filePath, [filename])
        else:
          #删除文件
          os.remove(filePath+"/" + filename)

  #清空接口调用文件
  def clear_interface(self, buildPath):
    self.clearFile(buildPath, ["upgrade/upgrade_Readme.md", "upgrade/4_apiUpgrade/global_api.json", "upgrade/4_apiUpgrade/tenantallin_api.json"])

  def clearFile(self, buildPath, filePaths):
    for filePath in filePaths:
      path = os.path.join(buildPath, filePath)
      if os.path.exists(path):
        file=open(path, "r+")
        file.truncate()


class CommentedTreeBuilder(ET.TreeBuilder):
  def __init__(self, element_factory=None):
    self.comment = self.handle_comment
    ET.TreeBuilder.__init__(self, element_factory)

  def handle_comment(self, data):
    self.start(ET.Comment, {})
    self.data(data)
    self.end(ET.Comment)


class VersionUtils():
  # 取指定的目录下的指定文件，递归查询子目录的级数为level
  def getxmlfile(self, path, level, fileNames):
    pomfiles = []
    files = os.listdir(path)
    for file in files:
      if file.startswith("."):
        continue
      sub = os.path.join(path, file)
      if os.path.isdir(sub):
        if (not file.startswith(".")) and level > 0:
          pomfiles = pomfiles + self.getxmlfile(sub, level - 1, fileNames)
      elif file in fileNames:
        pomfiles.append(sub)
    return pomfiles

  #修改parent(framework)的版本
  def updateParent(self, projectName, myroot, version):
    parentVerNode = myroot.find("{}parent/{}version".format(XML_NS_INC, XML_NS_INC))
    parentGroupIdNode = myroot.find("{}parent/{}groupId".format(XML_NS_INC, XML_NS_INC))
    if parentVerNode is not None:
      # 更新framework的version
      old = parentVerNode.text
      groupId = parentGroupIdNode.text
      if old != version and groupId == 'com.q7link.framework':
        parentVerNode.text = version
        print("工程【{}】【framework】版本修改为【{}】".format(projectName, version))
        return True
    return False

  #projectName:当前文件所属工程
  #myroot：xml文件
  #projectVersionMap：工程版本映射关系
  #propertieName：properties中的节点名称
  #targetProjectName：propertieName指代的是哪个工程版本
  def updateProperties(self, projectName, myroot, projectVersionMap, propertieName, targetProjectName):
    propertieVerNode = myroot.find("{}properties/{}{}".format(XML_NS_INC, XML_NS_INC, propertieName))
    update = False
    if propertieVerNode is not None:
      # 更新init-data的version
      old = propertieVerNode.text
      newVersion = projectVersionMap[targetProjectName]
      if old != newVersion:
        #不需要替换，并且版本不一致，则需要修改
        propertieVerNode.text = newVersion
        update = True
        print("工程【{}】【{}】版本修改为【{}】".format(projectName, targetProjectName, newVersion))
    return update

  #projectName:当前文件所属工程
  #myroot：xml文件
  #projectVersionMap：工程版本映射关系
  def updateDependencies(self, projectInfo, myroot, projectVersionMap, updateTest):
    update = False
    for dependencieNode in myroot.findall("{}dependencies/{}dependency".format(XML_NS_INC, XML_NS_INC)):
      versionNode = dependencieNode.find("{}version".format(XML_NS_INC))
      scopeNode = dependencieNode.find("{}scope".format(XML_NS_INC))
      groupId = dependencieNode.find("{}groupId".format(XML_NS_INC)).text

      if scopeNode is not None and not updateTest and scopeNode.text == 'test':
        #scope=test的版本不修改，由开发人员手动修改
        continue

      if groupId == 'com.q7link.application' and versionNode is not None:
        targetProjectName = dependencieNode.find("{}artifactId".format(XML_NS_INC)).text
        if targetProjectName.endswith("-private"):
          targetProjectName = targetProjectName[:-8]
          # print(targetProjectName)

        if targetProjectName in ['testapp','testapp-api','baseapp-api']:
          targetProjectName = 'framework'

        if targetProjectName in projectVersionMap:
          newVersion = projectVersionMap[targetProjectName]
          old = versionNode.text
          if projectInfo.getModule() == 'platform' and old.startswith('${'):
            #platform下的工程不替换变量版本
            continue
          if old != newVersion:
            #版本不一致，则需要修改
            versionNode.text = newVersion
            update = True
            print("工程【{}】【{}】版本修改为【{}】".format(projectInfo.getName(), targetProjectName, newVersion))
        else:
          print("ERROR: 工程【{}】【{}】的版本未找到！！！".format(projectInfo.getName(), targetProjectName, newVersion))
          sys.exit(1)
    return update

  def updatePlugin(self, projectName, myroot, projectVersionMap):
    update = False
    for pluginNode in myroot.findall("{}build/{}plugins/{}plugin".format(XML_NS_INC, XML_NS_INC,XML_NS_INC)):
      versionNode = pluginNode.find("{}version".format(XML_NS_INC))
      groupId = pluginNode.find("{}groupId".format(XML_NS_INC)).text

      if groupId == 'com.q7link.framework' and versionNode is not None:
        targetProjectName = 'framework';
        newVersion = projectVersionMap[targetProjectName]
        oldVersion = versionNode.text
        if oldVersion != newVersion and oldVersion != '${frameworkVersion}':
          #版本变动，需要修改
          versionNode.text = newVersion
          update = True
          print("工程【{}】【{}】版本修改为【{}】".format(projectName, targetProjectName, newVersion))
    return update


  # 对pom文件中的parent版本进行替换, 如果有替换，返回true, 否则返回false
  # config config.yaml文件内容
  def updateversion(self, projectInfo, myroot, projectVersionMap, changes, updateTest):
    projectName = projectInfo.getName()
    update = self.updateParent(projectName, myroot, projectVersionMap['framework'])
    for k,v in projectVersionMap.items():
      propertieName = utils.camel(k) + 'Version'
      if projectName != 'testapp' or propertieName != 'initDataVersion':
        # testapp的initData版本不修改
        update = self.updateProperties(projectName,myroot, projectVersionMap, propertieName, k) or update

    if projectName == 'parent':
      for change in changes:
        propertieName = 'version.framework.' + change.getName()
        update = self.updateProperties(projectName,myroot, projectVersionMap, propertieName, 'framework') or update
      update = self.updateProperties(projectName,myroot, projectVersionMap, 'version.framework', 'framework') or update
    update = self.updateDependencies(projectInfo, myroot, projectVersionMap, updateTest) or update

    return update

  # 对pom文件中工程自身版本进行替换, 如果有替换，返回true, 否则返回false
  # config config.yaml文件内容
  def updateselfversion(self, projectInfo, myroot, projectVersionMap):
    update = False
    projectName = projectInfo.getName()
    module = projectInfo.getModule()
    versionNode = myroot.find("{}version".format(XML_NS_INC, XML_NS_INC))

    if module == 'platform':
      version = projectVersionMap['framework']
    else:
      version = projectVersionMap[projectName]

    if versionNode is not None and version != versionNode.text:
      # 更新自身的version
      versionNode.text = version
      print("工程【{}】自身版本修改为【{}】".format(projectName, version))
      update = True
    return update


  # 对pom文件中的版本进行替换
  # config config.yaml文件内容
  def update(self, projectInfo, projectVersionMap, changes, updateTest):
    path = os.path.abspath(projectInfo.getPath())
    if not os.path.exists(path):
      print ("ERROR: 输入参数错误, 目录{}".format(path))
      sys.exit(1)
    # else:
    #   print ("处理目录{}".format(path))

    pomfiles =[]
    # 查找根目录及其子目录，只要pom.xml
    pomfiles.extend(self.getxmlfile(os.path.abspath(path), 1, ["pom.xml"]))
    ET.register_namespace("", XML_NS)
    if pomfiles == None:
      return
    for file in pomfiles:
      try:
        # mytree = ET.parse(file)
        mytree = ET.parse(file, parser=ET.XMLParser(target=CommentedTreeBuilder()))
        myroot = mytree.getroot()

        if self.updateversion(projectInfo, myroot, projectVersionMap, changes, updateTest):
          mytree.write(file, encoding="UTF-8", xml_declaration=True)

        if file.endswith('pom.xml') and projectInfo.getName()!='grpc-clients':
          if self.updateselfversion(projectInfo, myroot, projectVersionMap):
            mytree.write(file, encoding="UTF-8", xml_declaration=True)
      except BaseException as e:
        print ("update version of file {} failed, message: {}".format(file, e))
        traceback.print_exc()
        sys.exit(1)


#修改版本号
#例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
#python3 changeVersion.py hotfix true
if __name__ == "__main__":
  branchName=''
  needClear = False#是否清空开发脚本，默认false(不清空)
  if len(sys.argv) == 2 :
    branchName=sys.argv[1]
  elif len(sys.argv) == 3 :
    branchName=sys.argv[1]
    needClear = (sys.argv[2].lower() == 'true')
  else:
    print ("ERROR: 输入参数错误, 正确的参数为：<branch>")
    sys.exit(1)

  updateTest = False#是否更新测试包版本
  infos=branchName.split('.')
  if len(infos) > 1:
    branchName = infos[0]
    updateTest = infos[1].lower() == 'test'

  executor = ChangeVersion(branchName, updateTest, needClear)
  executor.execute()