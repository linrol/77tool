# coding=utf-8

import utils
import sys
import closeGit
from concurrent.futures import ThreadPoolExecutor, as_completed

class Checout:
  def __init__(self, branches, module=None, close=False, intersection=False):
    self.branches = branches
    self.branchNames = ".".join(branches)
    self.module = module
    self.is_front = module in ["front"]
    self.close = close
    self.intersection = intersection
    self.pool = ThreadPoolExecutor(max_workers=10)

  # 执行器
  def execute(self):
    if self.is_front:
      projectInfoMap = utils.project_path(self.module)
    else:
      projectInfoMap = utils.project_path()
    if len(projectInfoMap) == 0:
      sys.exit(1)

    projectMap = {}

    if "tag@" in self.branchNames:
      project_build = projectInfoMap.get("build")
      project_parent = projectInfoMap.get("parent")
      build_tag = self.branchNames.replace("tag@", "")
      project_tags = self.get_build_tags(project_build, project_parent, build_tag)
      tasks = [self.pool.submit(self.checkoutTag, projectInfo, project_tags) for projectInfo in projectInfoMap.values()]
    else:
      tasks = [self.pool.submit(self.checkoutBranch, projectInfo) for projectInfo in projectInfoMap.values()]
    for future in as_completed(tasks):
      result = future.result()
      if result is not None:
        projectMap[result.getName()] = result

    if close and len(projectMap) > 0:
      closeGit.close_git(projectMap)

  #检查是否有分支，如果有则检出分支
  def checkoutBranch(self, projectInfo):
    if self.intersection and not projectInfo.branchIntersection(self.branches):
        return None
    branch = projectInfo.getBranch(self.branchNames)
    if branch is not None:
      projectInfo.checkout(branch.name)
      print('工程【{}】检出分支【{}】成功'.format(projectInfo.getName(), branch.name))
      return projectInfo
    return None

  # 获取build工程指定tag的版本号
  def get_build_tags(self, project_build, project_parent, tag_name):
      project_build_tag = project_build.getTag(tag_name)
      if project_build_tag is None:
        raise Exception("工程【build】不存在标签【{}】".format(tag_name))
      tag_suffix = tag_name.rsplit("-")[1]
      yaml = utils.get_project_file(project_build, tag_name,
                                    'config.yaml', utils.yaml_parse)
      project_tags = {}
      for group, item in yaml.items():
        if type(item) is dict:
          for k, v in item.items():
            project_tags[k] = v + "-" + tag_suffix
      parent_tag = project_tags.get("framework")
      for k, v in self.get_platform_version(project_parent, parent_tag).items():
        project_tags[k] = v + "-" + tag_suffix
      project_tags["parent"] = parent_tag
      return project_tags

  # 获取parent工程下的版本号
  def get_platform_version(self, project_parent, tag_name):
    pom = utils.get_project_file(project_parent, tag_name,
                                 'pom.xml', utils.pom_parse)
    # 获取properties节点
    properties = pom.getElementsByTagName('properties')[0]
    platform_version = {}
    for node in properties.childNodes:
      nodeName = node.nodeName
      if nodeName.startswith("version.framework.") and node.nodeType == 1:
        k = nodeName.replace("version.framework.", "")
        platform_version[k] = node.firstChild.data
    return platform_version

  def checkoutTag(self, projectInfo, project_tags):
    project_name = projectInfo.getName()
    build_tag = self.branchNames.replace("tag@", "")
    if project_name == "build":
      tag_name = build_tag
    else:
      tag_name = project_tags.get(project_name, "")
    project_tag = projectInfo.getTag(tag_name)
    if project_tag is not None:
      projectInfo.checkoutTag(tag_name)
      print('工程【{}】检出标签【{}】成功'.format(projectInfo.getName(), tag_name))
      return projectInfo
    return None

#检出指定分支，支持设置git分支管理
#python3 checkout.py hotfix true
if __name__ == "__main__":
  if len(sys.argv) < 2:
    print ("ERROR: 输入参数错误, 正确的参数为：[module] <branch> [<closeGit>]")
    sys.exit(1)
  branchNames=sys.argv[1:]
  module = 'backend'
  close = False #是否需要关闭git管理
  if sys.argv[1] in ["backend", "front"]:
    module = sys.argv[1]
    branchNames.remove(module)
  if sys.argv[-1].lower() in ["true", "false"]:
    close = (sys.argv[-1].lower() == 'true')
    branchNames.remove(sys.argv[-1])
  check_intersection = len(branchNames) > 1 #是否检出交集分支
  executor = Checout(branchNames, module, close, check_intersection)
  executor.execute()

