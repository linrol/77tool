import utils
import sys
from common import Common


class Local(Common):
    def __init__(self):
        super().__init__(utils)

    def delete(self):
        for name, p in self.projects.items():
            p.deleteAllLocalBranch()


if __name__ == '__main__':
    try:
        if len(sys.argv) < 2:
            print("ERROR: 输入参数错误, 正确的参数为：<action>")
            sys.exit(1)
        action = sys.argv[1]
        local = Local()
        if action == "delete":
            local.delete()
    except Exception as err:
        print(err)
