# coding=utf-8

import os
import sys
import yaml
import gitlab
import subprocess
import utils
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BUILD_PATH='../../apps/build'

class CheckVersion:
  def __init__(self, project_names):
    self.pool = ThreadPoolExecutor(max_workers=100)
    self.project_names = project_names

    gl = gitlab.Gitlab(utils.URL, utils.TOKEN)
    gl.auth()
    self.gl = gl

    this_config_file = os.path.join(os.curdir, BUILD_PATH + '/config.yaml').replace("\\", "/")
    self.config_yaml = yaml.load(open(this_config_file), Loader=yaml.FullLoader)
    [result, this_branch] = subprocess.getstatusoutput('cd ' + BUILD_PATH +';git branch --show-current')
    self.this_branch = this_branch

  def branch_filter(self, branch):
    # 过滤半年以上未有提交的分支
    today = datetime.date.today()
    date1 = datetime.datetime.strptime(today.strftime("%Y-%m-%d"), "%Y-%m-%d")
    date2 = datetime.datetime.strptime(branch.commit.get("created_at")[0:10], "%Y-%m-%d")
    if(date1-date2).days < 180:
      return True
    else:
      return False

  def get_branches(self):
    branches = self.gl.projects.get(141).branches.list(all=True)
    return list(filter(self.branch_filter, branches))

  def get_branch_yaml(self, branch_name):
    f = self.gl.projects.get(141).files.get(file_path='config.yaml', ref=branch_name)
    config_yaml = yaml.load(f.decode() , Loader=yaml.FullLoader)
    return config_yaml

  def execute(self):
    # 遍历分支比较快照版本号是否重复
    check_result = True
    branches = self.get_branches()

    tasks = [self.pool.submit(self.check_version, branch.name) for branch in branches]

    for future in as_completed(tasks):
      res = future.result()
      if not res:
        check_result = False
    return check_result

  def check_version(self, branch_name):
    check_result = True
    if branch_name == self.this_branch:
      # 跳过当前分支
      return check_result
    # 获取对应分支的config.yaml进行版本号比较
    config_yaml = self.get_branch_yaml(branch_name)
    for category in config_yaml:
      projects = config_yaml.get(category)
      if isinstance(projects,list):
        continue
      for project in projects:
        version = projects.get(project)
        if "SNAPSHOT" not in version:
          continue
        if (len(self.project_names) > 0) and (project not in self.project_names):
          continue
        apps = self.config_yaml.get(category)
        if (apps is None):
          continue
        app_version = apps.get(project)
        if(app_version is None):
          continue
        if version == app_version:
          check_result = False
          print('工程【{}】版本号【{}】和分支【{}】冲突，请注意调整'.format(project, version, branch_name))
    return check_result

#检出指定分支，支持设置git分支管理
#python3 checkout.py hotfix true
if __name__ == "__main__":
  projectNames =[]
  if len(sys.argv) > 1:
    projectNames = sys.argv[1:]

  executor = CheckVersion(projectNames)
  if executor.execute():
   print('enjoy！版本号冲突检查通过')

