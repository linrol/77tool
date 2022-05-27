# coding=utf-8

import os
import sys
import yaml
import gitlab
import subprocess
import utils

BUILD_PATH='../../apps/build'

def get_branches():
  gl = gitlab.Gitlab(utils.URL, utils.TOKEN)
  gl.auth()
  branches = gl.projects.get(141).branches.list(all=True) # 此处是模糊查询
  return branches

def check_version(projectNames):
  gl = gitlab.Gitlab(utils.URL, utils.TOKEN)
  gl.auth()

  filename = os.path.join(os.curdir, BUILD_PATH + '/config.yaml').replace("\\", "/")
  config = yaml.load(open(filename), Loader=yaml.FullLoader)
  [result, this_branch] = subprocess.getstatusoutput('cd ' + BUILD_PATH +';git branch --show-current')

  # 遍历分支比较快照版本号是否重复
  branches = get_branches()
  check_result = True
  for branch in branches:
    # 跳过自身
    if branch.name == this_branch:
      continue
    f = gl.projects.get(141).files.get(file_path='config.yaml', ref=branch.name)
    yaml_file = yaml.load(f.decode() , Loader=yaml.FullLoader)
    for category in yaml_file:
      projects = yaml_file.get(category)
      if isinstance(projects,list):
        continue
      for project in projects:
        version = projects.get(project)
        if "SNAPSHOT" not in version:
          continue
        if (len(projectNames) > 0) and (project not in projectNames):
          continue
        if version == config.get(category).get(project):
          check_result = False
          print('工程【{}】版本号【{}】和分支【{}】冲突，请注意调整'.format(project, version, branch.name))
  return check_result

#检出指定分支，支持设置git分支管理
#python3 checkout.py hotfix true
if __name__ == "__main__":
  projectNames =[]
  if len(sys.argv) > 1:
    projectNames = sys.argv[1:]

  if check_version(projectNames):
    print('enjoy！版本号冲突检查全部通过')

