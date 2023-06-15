# coding:utf-8
import sys
import utils
from common import Common
from createBranch import CreateBranch
from checkanddeleted import DeleteBranch

XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"


class Backup(Common):
    def __init__(self, source, target, clear, namespaces):
        super().__init__(utils, "backend", False)
        self.source = source
        self.target = target
        self.clear = clear
        self.namespaces = namespaces

    def execute(self):
        backup_projects = []
        if not self.branch_is_presence(self.source):
            print("分支【{}】不存在".format(",".join(self.source)))
            sys.exit(1)
        if self.branch_is_presence(self.target):
            print("分支【{}】已存在，请删除后重试".format(self.target))
            sys.exit(1)
        for p, p_info in self.projects.items():
            if p_info.getModule() in self.namespaces:
                backup_projects.append(p)
            if p in self.namespaces:
                backup_projects.append(p)
        if len(backup_projects) < 1:
            print("分支【{}】不存在需要备份的工程组【{}】".format(self.source, ",".join(self.namespaces)))
            sys.exit(1)
        executor = CreateBranch(self.target, self.source, backup_projects, True)
        created_projects = executor.execute()
        gl_user_name = self.get_gl_user_name()
        created_value = "{}#{}#{}".format(self.source, gl_user_name, created_projects)
        key = "backend" + "@" + self.target
        self.hset('q7link-branch-created', key, created_value)
        print("基于【{}】创建分支【{}】工程【{}】成功".format(self.source, self.target,
                                                        created_projects))
        if not self.clear or self.is_trunk(self.source):
            return
        executor = DeleteBranch(self.source, self.target, backup_projects, True)
        executor.execute()
        print("删除【{}】分支的工程【{}】成功，该分支已合并至分支【{}】".format(self.source, created_projects.replace(",build", ""), self.target))


# 备份分支
# 例：备份sprint20220922分支的工程【global,framework,init-data】至stage-global
# python3 backup.py sprint20220922 stage-global global,framework
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("ERROR: 输入参数错误, 正确的参数为：<source_branch>[.clear] <target_branch> <module_namespaces>")
        sys.exit(1)
    else:
        clear_source = ".clear" in sys.argv[1]
        source_branch = sys.argv[1].replace(".clear", "")
        target_branch = sys.argv[2]
        module_namespaces = sys.argv[3].split(",")
        Backup(source_branch, target_branch, clear_source, module_namespaces).execute()
