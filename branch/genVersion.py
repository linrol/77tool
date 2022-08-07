# coding:utf-8
import os
import sys

import utils
import re
import yaml
import ruamel.yaml
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"

branch_weight = {"emergency": 1, "stage-patch": 1, "sprint": 5}
project_convert = ["app-build-plugins", "app-common", "baseapp-api", "common-base", "common-base-api", "graphql-api", "graphql-impl", "json-schema-plugin", "mbg-plugins", "metadata-api", "metadata-impl", "sql-parser"]
branch_group = {}
class GenVersion:
  def __init__(self, source_branch, target_branch, project_names):
    self.source_branch = source_branch
    self.target_branch = target_branch
    self.project_names, self.projects = self.pre_process(project_names)

    self.source_branch_version = self.get_branch_version(source_branch)
    self.target_branch_version = self.get_branch_version(target_branch, False)
    self.target_branch_name, self.target_branch_date = self.check_branch_before()
    self.pool = ThreadPoolExecutor(max_workers=10)

  def pre_process(self, project_names, ):
    result = set()
    target_branch_version = self.get_branch_version(self.target_branch, False)
    for project_name in project_names:
      if project_name in project_convert:
        project_name = "framework"
      target_project_version = target_branch_version.get(project_name)
      if target_project_version is None:
        # print("工程【】不存在".format(project_name))
        # sys.exit(1)
        continue
      # 过滤目标分支中已拉取过的工程
      if 'SNAPSHOT' in target_branch_version.get(project_name):
        # print("工程【】已存在目标分支{}版本号已更新过".format(project_name, self.target_branch))
        # sys.exit(1)
        continue
      result.add(project_name)
    return list(result), utils.project_path(set.union(result, {"build"}))

  def check_branch_before(self):
    check_error = "非值班分支，不支持自动生成版本号"
    if self.source_branch not in ['stage', 'master']:
      raise Exception(check_error)
    pattern = r"([a-zA-Z-]+|[20]\d{7})"
    target_branch_info = re.findall(pattern, self.target_branch)
    if len(target_branch_info) != 2:
      raise Exception(check_error)
    target_branch_name = target_branch_info[0]
    target_branch_date = target_branch_info[1]
    if target_branch_name not in ['emergency', 'sprint', 'stage-patch']:
      raise Exception(check_error)
    if target_branch_name + target_branch_date != self.target_branch:
      raise Exception(check_error)
    now=datetime.now().strftime("%Y%m%d")
    if(int(now) > int(target_branch_date)):
      raise Exception("拉取的目标分支小于当前日期，不支持自动生成版本号")
    return target_branch_name, target_branch_date

      #根据工程名称获取指定分支的远程文件
  def get_project_branch_file(self, project, branch_name, file_path):
    f = project.getProject().files.get(file_path=file_path, ref=branch_name)
    if f is None:
      raise Exception("工程【{}】分支【{}】不存在文件【{}】".format(project, branch_name, file_path))
    config_yaml = yaml.load(f.decode(), Loader=yaml.FullLoader)
    return config_yaml

  def write_build_version(self, branch_name, project_versions):
    self.projects.get('build').checkout(branch_name)
    config_yaml_path = os.path.join(os.curdir, '../../apps/build/config.yaml').replace("\\", "/")
    yaml = ruamel.yaml.YAML()
    config = yaml.load(open(config_yaml_path))
    for project, version in project_versions.items():
      group = branch_group.get(project)
      config[group][project] = version
    with open(config_yaml_path, 'w') as f:
      yaml.dump(config, f)

  #获取指定分支的版本号
  def get_branch_version(self, branch, get_min_version=True, config_yaml=None):
    build_project = utils.project_path('build').get('build')
    if build_project is None:
      raise Exception("工程【build】未找到，请检查git是否存在该项目")
    build_project_branch = build_project.getBranch(branch)
    if build_project_branch is None:
      raise Exception("工程【build】不存在分支【{}】".format(branch))
    if config_yaml is None:
      config_yaml = self.get_project_branch_file(build_project, branch, 'config.yaml')
    branch_version = {}
    for group, item in config_yaml.items():
      if type(item) is dict:
        for k, v in item.items():
          branch_group[k] = group
          if get_min_version:
            min_version = v.rsplit(".", 1)[1].replace('-SNAPSHOT', '').replace('.SNAPSHOT', '')
            if min_version.isdigit():
              branch_version[k] = int(min_version)
          else:
            branch_version[k] = v
    if len(branch_version) < 1:
      raise Exception("根据分支【{}】获取工程版本号失败".format(branch))
    return branch_version

  def factory_day(self):
    date_target=datetime.strptime(self.target_branch_date,"%Y%m%d")
    date_target=datetime(date_target[0], date_target[1], date_target[2])
    date_current=datetime.today()
    return (date_target-date_current).days + 1

  def factory_week(self):
    # week_start = datetime.strptime(start_time, '%Y%m%d')
    week_start = datetime.today()
    week_end = datetime.strptime(self.target_branch_date, '%Y%m%d')
    year_week_num = 52
    week_end_year = week_end.year
    week_start_year = week_start.year
    week_end_num = int(datetime.strftime(week_end, "%W"))
    week_start_num = int(datetime.strftime(week_start, "%W"))
    return (week_end_year - week_start_year) * year_week_num + week_end_num - week_start_num + 1

  def get_emergency_branch(self):
    try:
      emergency_branch_name = "emergency" + self.target_branch_date
      return self.get_branch_version(emergency_branch_name)
    except Exception as e:
      return None

  def get_replace_version(self, factory, project_name, emer_version):
    inc_min_version = factory * branch_weight.get(self.target_branch_name)
    source_min_version = self.source_branch_version.get(project_name)
    target_project_version = self.target_branch_version.get(project_name)
    if source_min_version is None:
      raise Exception("项目【{}】获取基础分支【{}】版本号失败".format(project_name, self.source_branch))

    # 当目标分支是stage-patch开头，版本号=(branch_weight * day) + emergency.inc_version
    # 不存在emergency分支 or 不存在emergency分支的工程
    if emer_version is not None and emer_version.get(project_name) is not None:
      inc_min_version += emer_version.get(project_name)
    else:
      inc_min_version += source_min_version
    replace_version = str(inc_min_version) + '-SNAPSHOT'
    return replace_version.join(target_project_version.rsplit(str(source_min_version), 1))

  def execute(self):
    emergency_branch_version = None
    if self.target_branch_name in ['sprint']:
      factory = self.factory_week()
    else:
      factory = self.factory_day()
    if self.target_branch_name in ["stage-patch"]:
      emergency_branch_version = self.get_emergency_branch()
    update_version = {}
    for project_name in self.project_names:
      version = self.get_replace_version(factory, project_name, emergency_branch_version)
      update_version[project_name] = version
    self.write_build_version(self.target_branch, update_version)
    return update_version

#修改版本号
#例：修改hotfix分支的版本号，并且修改工程自身版本号，清空开发脚本
#python3 changeVersion.py hotfix true
if __name__ == "__main__":
  if len(sys.argv) < 4:
    print("ERROR: 输入参数错误, 正确的参数为：<source_branch> <target_branch> [project...]")
    sys.exit(1)
  project_names = []
  if len(sys.argv) > 3:
    project_names = sys.argv[3:]
  GenVersion(sys.argv[1], sys.argv[2], project_names).execute()