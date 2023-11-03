import requests
import json

NEXUS_URL = 'http://nexus.q7link.com:8081'
auth = ('branch-ci', 'branch-ci')
GROUP_ID = 'com.q7link.application'


def search(repository, group_id, artifact_id, version):
    search_url = "{}/service/rest/v1/search?repository={}&maven.groupId={}&maven.artifactId={}&maven.extension=jar&version={}".format(NEXUS_URL, repository, group_id, artifact_id, version)
    headers = {'content-type': 'application/json', 'charset': 'utf-8'}
    response = requests.get(search_url, auth=auth, headers=headers)
    data = json.loads(response.content.decode())
    print(data)
    return data


def delete(module_id):
    delete_url = "{}/service/rest/v1/components/{}".format(NEXUS_URL, module_id)
    headers = {'content-type': 'application/json', 'charset': 'utf-8'}
    print(delete_url)
    response = requests.delete(delete_url, auth=auth, headers=headers)
    return response.status_code == 204


def delete(repository, group_id, artifact_id, version):
    ret = search(repository, group_id, artifact_id, version)
    items = ret.get('items')
    if len(items) != 1:
        print("not found jar")
    else:
        item_id = items[0].get("id")
        ret = delete(item_id)
        print("delete ret {}".format(ret))


if __name__ == '__main__':
    delete("maven-releases", GROUP_ID, "budget-api", "1.26.3")
