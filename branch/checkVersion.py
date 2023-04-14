# coding=utf-8
import datetime
import getopt
import sys
import uuid
from itertools import zip_longest
from concurrent.futures import ThreadPoolExecutor, as_completed

import utils
from common import Common, LinkedList


def usage():
    print('''
    -h --help show help info
    -t --type check type for version duplicate or compare
    -p --project check project for version duplicate
    -b --branch check branch for version duplicate or compare
    ''')
    sys.exit(1)
    pass


def branch_filter(branch):
    # 过滤半年以上未有提交的分支
    today = datetime.date.today()
    date1 = datetime.datetime.strptime(today.strftime("%Y-%m-%d"),
                                       "%Y-%m-%d")
    date2 = datetime.datetime.strptime(branch.commit.get("created_at")[0:10], "%Y-%m-%d")
    return (date1 - date2).days < 180


class CheckVersion(Common):
    def __init__(self, project_names=None):
        super().__init__(utils)
        self.project_names = project_names
        self.pool = ThreadPoolExecutor(max_workers=10)

    # 根据工程名称获取所有的分支
    def get_project_branches(self):
        branches = self.project_build.getProject().branches.list(all=True)
        return list(filter(branch_filter, branches))

    def check_duplicate(self, target_branch):
        # 遍历分支比较快照版本号是否重复
        is_duplicate = False
        branches = self.get_project_branches()
        target_branch_version = self.get_branch_version(target_branch, True)

        tasks = [self.pool.submit(self.is_duplicate, branch.name, target_branch, target_branch_version) for branch in branches]
        for future in as_completed(tasks):
            if future.result():
                is_duplicate = True
        return is_duplicate

    def is_duplicate(self, check_branch, target_branch, target_version):
        is_duplicate = False
        check_msg = "工程【{}】的版本号【{}】和分支【{}】冲突，请注意调整"
        if len(target_version) < 1:
            return is_duplicate
        if check_branch == target_branch:
            # 跳过被比较的分支
            return is_duplicate
        if self.project_build.getBranch(check_branch) is None:
            # 不存在build工程的分支
            return is_duplicate
        # 获取对应分支的config.yaml进行版本号比较
        check_version = self.get_branch_version(check_branch, True)
        if len(check_version) < 1:
            return is_duplicate
        for p_name, t_version in target_version.items():
            # 指定检查的项目
            if self.project_names is not None:
                if p_name not in self.project_names.split(","):
                    continue
            c_version = check_version.get(p_name, None)
            if c_version is None:
                continue
            p_git = self.projects.get(p_name, None)
            if c_version[0] == t_version[0] and c_version[1] == t_version[1]:
                if p_git is None:
                    is_duplicate = True
                    print(check_msg.format(p_name, "{}.{}".format(t_version[0], t_version[1]), check_branch))
                elif p_git.getBranch(check_branch) is not None and \
                     p_git.getBranch(target_branch) is not None:
                    is_duplicate = True
                    print(check_msg.format(p_name, "{}.{}".format(t_version[0], t_version[1]), check_branch))
        return is_duplicate

    def compare_version(self, branch_dict, is_correct=False):
        correct = {}
        compare_ret = set()
        compare_msg = "工程【{}】分支版本号【{}】落后于分支版本号【{}】"
        project_version = {}
        for b_name, skip_release in branch_dict.items():
            if self.project_build.getBranch(b_name) is None:
                continue
            branch_version = self.get_branch_version(b_name, skip_release)
            for p, p_version in branch_version.items():
                if p == "reimburse":
                    continue
                data = {"branch": b_name, "version": p_version}
                project_version.setdefault(p, LinkedList()).append(data)
        for p, link in project_version.items():
            node = link.head
            while node is not None:
                if not node.before_next():
                    node = node.next
                    continue
                compare_ret.add(p)
                print(compare_msg.format(p, node, node.next))
                if not is_correct:
                    node = node.next
                    continue
                weight = self.get_branch_weight('', node.branch, '')
                correct_p_v = p + ":" + node.inc_next_version(weight)
                correct.setdefault(node.branch, []).append(correct_p_v)
                node = node.next
        host = "https://branch.linrol.cn/branch/correct?correct_id={}&user_id=&branch={}&project={}"
        correct_msg = "======================================" + \
                      "\n是否自动校正【{}】分支版本号\n" + \
                      "<a href=\"{}\">点击校正</a>"
        for b, pv in correct.items():
            correct_id = ''.join(str(uuid.uuid4()).split('-'))
            correct_url = host.format(correct_id, b, ",".join(pv))
            print(correct_msg.format(b, correct_url))
        return compare_ret


# python3 checkVersion.py branch [project...]
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ht:p:b:", ["help", "type=", "project=", "branch="])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(1)
    project = None
    check_type = None
    branch = None
    for k, v in opts:
        if k in ("-h", "--help"):
            usage()
        elif k in ("-t", "--type"):
            check_type = v
        elif k in ("-p", "--project"):
            project = v
        elif k in ("-b", "--branch"):
            branch = v
        else:
            usage()

    check = CheckVersion(project)
    if check_type == "duplicate":
        if check.check_duplicate(branch):
            sys.exit(1)
        print('enjoy！版本号冲突检查通过')
    elif check_type == "compare":
        compare_dict = dict(zip_longest(branch.split(","), [], fillvalue=True))
        if len(check.compare_version(compare_dict, True)) > 0:
            sys.exit(1)
        print('enjoy！版本号比较检查通过')
    else:
        usage()

