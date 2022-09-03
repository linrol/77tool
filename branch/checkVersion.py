# coding=utf-8

import datetime
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import utils
from common import Common

exclude_project = ["framework", "  reimburse"]


def branch_filter(branch):
    # 过滤半年以上未有提交的分支
    today = datetime.date.today()
    date1 = datetime.datetime.strptime(today.strftime("%Y-%m-%d"),
                                       "%Y-%m-%d")
    date2 = datetime.datetime.strptime(
        branch.commit.get("created_at")[0:10], "%Y-%m-%d")
    return (date1 - date2).days < 180


def print_error(project, version, branch):
    print('工程【{}】的版本号【{}】和分支【{}】冲突，请注意调整'.format(project,
                                                               version,
                                                               branch))


class CheckVersion(Common):
    def __init__(self, target_branch, project_names):
        super().__init__(utils)
        self.pool = ThreadPoolExecutor(max_workers=100)
        self.target_branch = target_branch
        self.project_names = project_names
        self.target_branch_version = self.get_branch_version(target_branch,
                                                             True)

    # 根据工程名称获取所有的分支
    def get_project_branches(self):
        branches = self.project_build.getProject().branches.list(all=True)
        return list(filter(branch_filter, branches))

    def execute(self):
        # 遍历分支比较快照版本号是否重复
        check_result = True
        branches = self.get_project_branches()

        tasks = [self.pool.submit(self.check_version, branch.name) for branch in
                 branches]

        for future in as_completed(tasks):
            res = future.result()
            if not res:
                check_result = False
        return check_result

    def check_version(self, check_branch):
        check_result = True
        if len(self.target_branch_version) < 1:
            return check_result
        if check_branch == self.target_branch:
            # 跳过被比较的分支
            return check_result
        if self.project_build.getBranch(check_branch) is None:
            # 不存在build工程的分支
            return check_result
        # 获取对应分支的config.yaml进行版本号比较
        check_branch_version = self.get_branch_version(check_branch, True)
        if len(check_branch_version) < 1:
            return check_result
        for k, v in self.target_branch_version.items():
            if len(self.project_names) > 0 and k not in projectNames:
                continue
            version = check_branch_version.get(k, None)
            if version is None:
                continue
            project = self.projects.get(k, None)
            if version[0] == v[0] and version[1] == v[1]:
                if project is None:
                    print_error(k, "{}.{}".format(v[0], v[1]), check_branch)
                    check_result = False
                elif project.getBranch(check_branch) is not None and \
                     project.getBranch(self.target_branch) is not None:
                    print_error(k, "{}.{}".format(v[0], v[1]), check_branch)
                    check_result = False
        return check_result


# python3 checkVersion.py branch [project...]
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: 输入参数错误, 正确的参数为：<check_branch> [project...]")
        sys.exit(1)
    branch_name = sys.argv[1]
    projectNames = []
    if len(sys.argv) > 2:
        projectNames = sys.argv[2:]

    executor = CheckVersion(branch_name, projectNames)
    if executor.execute():
        print('enjoy！版本号冲突检查通过')
