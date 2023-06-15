# coding=utf-8

import utils
import sys
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ElementTree,Element

def close_git(projectMap):
  if len(projectMap) == 0:
    return
  print('Git管理：' + str(list(projectMap.keys())))

  path = '../../.idea'
  xmlName = 'vcs.xml'

  tree = ET.parse('{}/{}'.format(path,xmlName))
  root=tree.getroot()
  components=root.findall('component')
  for component in components:
    name = component.get("name")
    if name == 'VcsDirectoryMappings':
      break

  mappings = component.iter('mapping')
  for mapping in list(mappings):
    directory = mapping.get('directory')
    projectName = directory[directory.rfind('/') + 1:]
    if projectName in projectMap:
      mapping.set('vcs', 'Git')
      del projectMap[projectName]
    else:
      component.remove(mapping)

  for projectName,projectInfo in projectMap.items():
    dirNames = projectInfo.getPath().split('/')
    element = Element('mapping', {'directory':'$PROJECT_DIR$/{}/{}'.format(dirNames[-2], dirNames[-1]), 'vcs':'Git'})
    element.tail = '\n    '
    component.append(element)

  tree.write('{}/{}'.format(path,xmlName), encoding="UTF-8", xml_declaration=True)


#关闭没有指定分支的工程 git管理功能
#python3 closeGit.py hotfix
if __name__ == "__main__":

  branchName=''
  if len(sys.argv) == 2 :
    branchName=sys.argv[1]
  else:
    print ("ERROR: 输入参数错误, 正确的参数为：<branch>")
    sys.exit(1)


  projectInfoMap = utils.init_projects()
  if len(projectInfoMap) == 0:
    sys.exit(1)

  projectMap = {}

  for projectName,projectInfo in projectInfoMap.items():
    branch = projectInfo.getBranch(branchName)
    if branch is None:
      continue
    else:
      projectMap[projectName] = projectInfo

  close_git(projectMap)
  print('Git管理成功')
