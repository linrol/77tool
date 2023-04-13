# -*- coding: utf-8 -*-
import os
import sys

# 工程查找深度
FIND_DEPTH = 3
# 合并代码的工程
PROJECT_DIR = 'D:/merge_project'


# 递归访问文件夹
def access_dir_recursively(base_dir, access_fun, depth=0):
    if depth == FIND_DEPTH:
        return
    access_fun(base_dir)
    dir_children = os.listdir(base_dir)
    for dir_child in dir_children:
        full_path = os.path.join(base_dir, dir_child)
        if not os.path.isdir(full_path):
            continue
        access_dir_recursively(full_path, access_fun, depth + 1)


def get_git_info(dir_path):
    output = os.popen('cd ' + dir_path + ' & git config --local --list')
    output_lines = output.readlines()
    result = {}
    for line in output_lines:
        key_values = line.split('=')
        result[key_values[0]] = key_values[1].strip()
    return result


def current_branch(dir_path):
    output = os.popen('cd ' + dir_path + ' & git branch')
    output_lines = output.readlines()
    for line in output_lines:
        if line.__contains__('*'):
            return line.split(' ')[1].strip()


def make_link(path, target):
    path_splits = os.path.split(path)
    dir_name = path_splits[len(path_splits) - 1]
    os.popen('mklink /D "' + os.path.join(target, dir_name) + '" "' + path + '"')


def access_dir(dir_path):
    if not is_git_project(dir_path):
        return
    branch = current_branch(dir_path)
    target_branch = sys.argv[1] if len(sys.argv) > 1 else ''
    if branch == target_branch:
        make_link(dir_path, PROJECT_DIR)


def is_git_project(dir_path):
    if os.path.exists(os.path.join(dir_path, '.git')):
        return True
    return False


if __name__ == '__main__':
    os.remove(PROJECT_DIR)
    os.makedirs(PROJECT_DIR)
    current_dir = os.path.abspath('../../')
    access_dir_recursively(current_dir, access_dir)
