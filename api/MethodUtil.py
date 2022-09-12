from types import MethodType

# 获取项目成员
def getMember(self, query):
    if query is None:
        return None
    members = self.getProject().members_all.list(query=query)
    if members is not None and len(members) > 0:
        return members[0]
    return None

# 创建合并
def createMrRequest(self, source, target, title, assignee):
    data = {
        'source_branch': source,
        'target_branch': target,
        'title': title,
        'remove_source_branch': True
    }
    member = self.getMember(assignee)
    if member is not None:
        data['assignee_id'] = member.id
    return self.getProject().mergerequests.create(data)

def add_method(project):
    project.getMember = MethodType(getMember, project)
    project.createMrRequest = MethodType(createMrRequest, project)



