import os
import xml.etree.ElementTree as et
from common import Common
XML_NS = "http://maven.apache.org/POM/4.0.0"
XML_NS_INC = "{http://maven.apache.org/POM/4.0.0}"
class Dependency(Common):

    def __init__(self):
        self.ignore = ['grpc-clients', 'testapp', 'base-common-test', 'idgen-client', 'crypto', 'autotest-frame-starter']
        super().__init__()

    def getfile(self, path, level, file_names):
        pom = []
        files = os.listdir(path)
        for file in files:
            if file.startswith("."):
                continue
            sub = os.path.join(path, file)
            if os.path.isdir(sub):
                if (not file.startswith(".")) and level > 0:
                    pom = pom + self.getfile(sub, level - 1, file_names)
            if file in file_names:
                pom.append(sub)
        return pom

    def get_artifact_list(self, nodes):
        artifact_list = []
        for node in nodes:
            group_node = node.find("{}groupId".format(XML_NS_INC))
            if group_node is None:
                continue
            artifact_node = node.find("{}artifactId".format(XML_NS_INC))
            if artifact_node is None:
                continue
            group = group_node.text
            artifact = artifact_node.text
            scope = node.find("{}scope".format(XML_NS_INC))
            if not group.startswith("com.q7link"):
                continue
            if artifact.endswith("-private"):
                continue
            if artifact in self.ignore:
                continue
            if scope is not None and scope.text == "test":
                continue
            artifact_list.append(artifact)
        return artifact_list
    def cal(self, branch):
        # self.checkout_branch("{}.stage".format(branch))
        et.register_namespace("", XML_NS)
        dependencies = {}
        for project in self.projects.values():
            if project.getName() in self.ignore:
                continue
            path = project.getPath()
            if path is None:
                continue
            if project.getEnd() != self.backend:
                continue
            poms = self.getfile(os.path.abspath(path), 1, ["pom.xml"])
            for pom in poms:
                artifact_list = []
                tree = et.parse(pom, parser=et.XMLParser(target=Builder()))
                root = tree.getroot()
                module = root.find("{}artifactId".format(XML_NS_INC, XML_NS_INC)).text
                parent_module = root.find("{}parent/{}artifactId".format(XML_NS_INC, XML_NS_INC))
                if parent_module is not None:
                    parent_group = root.find("{}parent/{}groupId".format(XML_NS_INC, XML_NS_INC)).text
                    if parent_group.startswith("com.q7link"):
                        artifact_list.append(parent_module.text)
                nodes = root.findall("{}dependencies/{}dependency".format(XML_NS_INC, XML_NS_INC))
                artifact_list.extend(self.get_artifact_list(nodes))
                nodes = root.findall("{}build/{}plugins/{}plugin".format(XML_NS_INC, XML_NS_INC, XML_NS_INC))
                artifact_list.extend(self.get_artifact_list(nodes))
                if module == "app-common-api":
                    artifact_list.append("init-data")
                dependencies[module] = artifact_list
        node = DependencyNode().gen(dependencies, None)
        weight = 500
        while node is not None:
            print("weight:{}, projects:{}".format(weight, node.data))
            node = node.after
            weight -= 20


class Builder(et.TreeBuilder):
    def __init__(self, element_factory=None):
        self.comment = self.handle_comment
        et.TreeBuilder.__init__(self, element_factory)

    def handle_comment(self, data):
        self.start(et.Comment, {})
        self.data(data)
        self.end(et.Comment)


class DependencyNode(object):
    def __init__(self, data=None, before=None):
        self.data = data
        self.before = before
        self.after = None

    def gen(self, data, before):
        ret = []
        for k, v in data.items():
            if v is None or len(v) == 0:
                ret.append(k)
                continue
            before_vs = self.get_before_data(before, list())
            diff = set(v) - set(before_vs)
            if len(diff) == 0:
                ret.append(k)
                continue
            unknown = diff - data.keys()
            if len(unknown) > 0:
                print("工程【{}】依赖的【{}】不存在".format(k, unknown))
                exit(-1)
        if len(ret) == 0:
            loop_path = "->".join(self.get_loop_path(data, list(data.values())[0], []))
            print("工程存在循环依赖，无法生成有向图({})".format(loop_path))
            exit(-1)
        ret.sort()
        node = DependencyNode(ret, before)
        for k in ret:
            data.pop(k)
        if len(data) > 0:
            node.after = self.gen(data, node)
        return node

    def get_before_data(self, before, v):
        if before is None:
            return v
        v.extend(before.data)
        return self.get_before_data(before.before, v)

    def get_loop_path(self, data, p_list, path):
        for p in p_list:
            if p not in data.keys():
                continue
            if p in path:
                return path
            path.append(p)
            return self.get_loop_path(data, data.get(p), path)


if __name__ == '__main__':
    Dependency().cal("sprint20231106")
