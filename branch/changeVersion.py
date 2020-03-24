# coding:utf-8
# 修改所有项目依赖的framework版本
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
def get_project_version(branchName, projectPaths):
  buildName = 'build'
  if buildName in projectPaths.keys():
    buildPath = projectPaths[buildName]
    build = utils.get_project(buildName)
    buildBranch = utils.check_branch_exist(build, branchName)
    if buildBranch is None:
      print('ERROR: 工程【build】不存在分支【{}】'.format(branchName))
      sys.exit(1)
    else:
      cmd = 'cd ' + buildPath + ';git checkout ' + branchName + '; git pull'
      [result, msg] = subprocess.getstatusoutput(cmd)
      if result != 0:
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
def get_project(branchName, projectPaths):
  error=[]
  projectMap ={}
  for k,v in projectPaths.items():
    project = utils.get_project(k)
    if project is None :
      error.append('工程【{}】不存在'.format(k))
      continue
    else:
      branch = utils.check_branch_exist(project, branchName)
      #有指定分支的项目切换到指定分支
      if (branch is None):
        continue
      else:
        cmd = 'cd ' + v + ';git checkout ' + branchName + '; git pull'
        [result, msg] = subprocess.getstatusoutput(cmd)
        if result != 0:
          error.append('工程【{}】检出分支【{}】失败'.format(k, branchName))
          continue
        else:
          projectMap[project.name] = v

  if len(error) > 0:
    #如果有错误信息则不执行
    utils.print_list("ERROR: ", error)
    sys.exit(1)
  else:
    return projectMap

#清空开发脚本
def clear_script(buildPath):
  childPaths = ['1_before', '2_after', 'recovery']
  for itemPath in childPaths:
    filePath = buildPath + "/upgrade/" + itemPath
    fileNames = os.listdir(filePath)
    for filename in fileNames:
      if (filename.lower().find('identity') != -1) or (filename.lower().find('reconcile') != -1) or (filename.lower().find('tenantallin') != -1) :
        #清空文件内容
        file=open(filePath+"/" + filename, "r+")
        file.truncate()
      else:
        #删除文件
        os.remove(filePath+"/" + filename)

#清空接口调用文件
def clear_interface(buildPath):
  filePath = buildPath + "/upgrade"
  file=open(filePath+"/upgrade_Readme.md", "r+")
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
  #isReplace：版本和本工程相同时，是否替换为${project.version}
  def updateProperties(self, projectName, myroot, projectVersionMap, propertieName, targetProjectName, isReplace):
    propertieVerNode = myroot.find("{}properties/{}{}".format(XML_NS_INC, XML_NS_INC, propertieName))
    update = False
    if propertieVerNode is not None:
      # 更新init-data的version
      old = propertieVerNode.text
      newVersion = projectVersionMap[targetProjectName]
      if (not isReplace) and old != newVersion:
        #不需要替换，并且版本不一致，则需要修改
        propertieVerNode.text = newVersion
        update = True
        print("工程【{}】【{}】版本修改为【{}】".format(projectName, targetProjectName, newVersion))
      elif isReplace and projectVersionMap[projectName] == newVersion:
        #需要替换，并且本工程版本号与目标工程版本号一致
        if old != '${project.version}' and old != newVersion:
          #旧版本设置的不是${project.version}，则需要设置为${project.version}
          propertieVerNode.text = '${project.version}'
          update = True
          print("工程【{}】【{}】版本修改为【{}】".format(projectName, targetProjectName, '${project.version}'))
      elif isReplace and old !=newVersion:
        #需要替换，并且本工程版本号与目标工程版本号不一致，则替换为新版本号
        propertieVerNode.text = newVersion
        update = True
        print("工程【{}】【{}】版本修改为【{}】".format(projectName, targetProjectName, newVersion))
    return update

  #projectName:当前文件所属工程
  #myroot：xml文件
  #projectVersionMap：工程版本映射关系
  #isReplace：版本和本工程相同时，是否替换为${project.version}
  def updateDependencies(self, projectName, myroot, projectVersionMap, isReplace):
    update = False
    for dependencieNode in myroot.findall("{}dependencies/{}dependency".format(XML_NS_INC, XML_NS_INC)):
      versionNode = dependencieNode.find("{}version".format(XML_NS_INC))
      groupId = dependencieNode.find("{}groupId".format(XML_NS_INC)).text

      if groupId == 'com.q7link.application' and versionNode is not None:
        artifactId = dependencieNode.find("{}artifactId".format(XML_NS_INC)).text
        targetProjectName = '';
        if artifactId.endswith('-api'):
          targetProjectName = artifactId[:-4]
        else:
          targetProjectName = artifactId

        if targetProjectName in projectVersionMap:
          newVersion = projectVersionMap[targetProjectName]
          old = versionNode.text
          if (not isReplace) and old != newVersion:
            #不需要替换，并且版本不一致，则需要修改
            versionNode.text = newVersion
            update = True
            print("工程【{}】【{}】版本修改为【{}】".format(projectName, targetProjectName, newVersion))
          elif isReplace and projectVersionMap[projectName] == newVersion:
            #需要替换，并且本工程版本号与目标工程版本号一致
            if old != '${project.version}' and old != newVersion:
              #旧版本设置的不是${project.version}，则需要设置为${project.version}
              versionNode.text = '${project.version}'
              update = True
              print("工程【{}】【{}】版本修改为【{}】".format(projectName, targetProjectName, '${project.version}'))
          elif isReplace and old !=newVersion:
            #需要替换，并且本工程版本号与目标工程版本号不一致，则替换为新版本号
            versionNode.text = newVersion
            update = True
            print("工程【{}】【{}】版本修改为【{}】".format(projectName, targetProjectName, newVersion))
        else:
          print("ERROR: 工程【{}】【{}】的版本未找到！！！".format(projectName, targetProjectName, newVersion))
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
  def updateversion(self, projectName, myroot, projectVersionMap):
    update = self.updateParent(projectName, myroot, projectVersionMap['framework'])
    if projectName == 'framework':
      update = self.updateProperties(projectName,myroot, projectVersionMap, 'version.framework', 'framework', False) or update
    if projectName == 'init-data':
      update = self.updateProperties(projectName,myroot, projectVersionMap, 'frameworkVersion', 'framework', False) or update
      update = self.updatePlugin(projectName, myroot, projectVersionMap) or update
    if projectName == 'finance' or projectName == 'basebi':
      update = self.updateDependencies(projectName, myroot, projectVersionMap, True) or update

    return update

  # 对pom文件中工程自身版本进行替换, 如果有替换，返回true, 否则返回false
  # config config.yaml文件内容
  def updateselfversion(self, projectName, myroot, projectVersionMap):
    update = False
    parentVerNode = myroot.find("{}version".format(XML_NS_INC, XML_NS_INC))

    if parentVerNode is not None and projectVersionMap[projectName] != parentVerNode.text:
      # 更新自身的version
      parentVerNode.text = projectVersionMap[projectName]
      print("工程【{}】自身版本修改为【{}】".format(projectName,projectVersionMap[projectName]))
      update = True
    return update


  # 对pom文件中的版本进行替换
  # config config.yaml文件内容
  def update(self, projectName, relpath, projectVersionMap, updateSelf):
    path = os.path.abspath(relpath)
    if not os.path.exists(path):
      print ("ERROR: 输入参数错误, 目录{}".format(path))
      sys.exit(1)
    # else:
    #   print ("处理目录{}".format(path))

    pomfiles =[]
    # 查找一级目录，只要pom.xml
    if projectName == 'init-data':
      pomfiles = self.getxmlfile(os.path.abspath(os.path.join(path,"src/main/resources")), 0, ['dump.xml','dump4unpack.xml'])
    elif projectName == 'framework':
      pomfiles = self.getxmlfile(os.path.abspath(os.path.join(path,"common-base-api/src/main/resources")), 0, ['pom-gen.xml','pom-gen-impl.xml'])
      pomfiles.extend(self.getxmlfile(os.path.abspath(os.path.join(path,"testapp/api")), 0, ['pom.xml']))
      pomfiles.extend(self.getxmlfile(os.path.abspath(os.path.join(path,"testapp/testapp")), 0, ['pom.xml']))

    pomfiles.extend(self.getxmlfile(os.path.abspath(path), 1, ["pom.xml"]))
    ET.register_namespace("", XML_NS)
    if pomfiles == None:
      return
    for file in pomfiles:
      try:
        # mytree = ET.parse(file)
        mytree = ET.parse(file, parser=ET.XMLParser(target=CommentedTreeBuilder()))
        myroot = mytree.getroot()

        if self.updateversion(projectName, myroot, projectVersionMap):
          mytree.write(file, encoding="UTF-8", xml_declaration=True)

        if updateSelf and file.endswith('pom.xml'):
          if self.updateselfversion(projectName, myroot, projectVersionMap):
            mytree.write(file, encoding="UTF-8", xml_declaration=True)
      except BaseException as e:
        print ("update version of file {} failed, message: {}".format(file, e))
        traceback.print_exc()
        sys.exit(1)


#修改版本号
#例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
#python3 changeVersion.py hotfix.self true
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

  updateSelf = False#是否更新自身版本
  infos=branchName.split('.')
  if len(infos) > 1:
    branchName = infos[0]
    updateSelf = True

  #获取所有工程的本地路径
  projectPaths = utils.project_path()
  if len(projectPaths) > 0:
    projectMap = get_project(branchName, projectPaths)
    projectVersionMap = get_project_version(branchName, projectPaths)

    #根据config.yaml修改拥有指定分支的工程依赖版本
    util = VersionUtils()
    for k,v in projectMap.items():
      if k == "framework" and not updateSelf:
        # framework不更新
        continue
      util.update(k, v, projectVersionMap, updateSelf)

    #清空开发脚本及接口调用信息
    if needClear and ('build' in projectMap):
      clear_script(projectPaths['build'])
      clear_interface(projectPaths['build'])
  else:
    print('ERROR: 请在path.yaml文件配置各项目路径！！！')
    sys.exit(1)