# coding:utf-8
import sys
import getopt
import utils
import traceback
import requests
import uuid
from common import Common
from datetime import datetime, timedelta


def usage():
    print('''
    -h --help show help info
    -f --force update version
    -s --source update from branch version
    -t --target update to branch version
    -p --project gen project list
    ''')
    sys.exit(1)
    pass


class GenVersion(Common):
    def __init__(self, target):
        super().__init__(utils)
        self.target = target
        self.target_version = self.get_branch_version(target)

    def execute(self):
        try:
            gen_version = {}
            for k, v in self.target_version.items():
                if self.project_branch_is_presence(k, self.target):
                    gen_version[k] = "{}.{}".format(v[0], int(v[1]) + 1)
            self.update_build_version(self.target, gen_version)
            return gen_version
        except Exception as e:
            print(str(e))
            traceback.print_exc()
            sys.exit(1)


# 生成版本号
if __name__ == "__main__":
    try:
        GenVersion('release20230921').execute()
    except getopt.GetoptError as err:
        print(err)
        traceback.print_exc()
        usage()
        sys.exit(1)
