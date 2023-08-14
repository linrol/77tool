# 引入第三方库 requests
import requests

import re
import math
import json


ARTIFACT_ID = 'project'
GROUP_ID = 'com.q7link.application'

NEXUS_URL = 'http://nexus.q7link.com:8081/service/extdirect'
NEXUS_COOKIE = 'onetwothree'


def main(artifact_id, group_id, version):
    # 从nexus获取指定项目的所有版本号
    version_list = __get_version_list(ARTIFACT_ID, GROUP_ID, NEXUS_URL, NEXUS_COOKIE)

    # 计算出最大的版本号
    max_version = __get_max_version(version_list)
    print('最新的版本号 >>>   ' + max_version)


# 从集合中，查找出最大的版本号
def __get_max_version(version_list):
    # 初始值设为 0.0.0
    # 数据格式为 ('完整的版本号'，主版本号, 次版本号, 小版本号)
    max_version_tup = ('0.0.0', 0, 0, 0)

    for current_version in version_list:
        # 对于形如 1.1.0-SNAPSHOT 的版本号，转换成 1.1.0
        temp_version = re.sub('-.*', '', current_version)
        num_list = temp_version.split('.')
        current_version_tup = [current_version, int(num_list[0]), int(num_list[1]), int(num_list[2])]

        # 与上一次记录的最大版本号比较，取二者最大值，作为最新的最大版本号
        max_version_tup = __get_max_version_tup(max_version_tup, current_version_tup)

    return max_version_tup[0]


# 比较两个版本号，返回其中的最大者
def __get_max_version_tup(tup_a, tup_b):
    # 依次比较3个版本号
    if tup_a[1] > tup_b[1]:
        return tup_a
    if tup_a[1] < tup_b[1]:
        return tup_b

    if tup_a[2] > tup_b[2]:
        return tup_a
    if tup_a[2] < tup_b[2]:
        return tup_b

    if tup_a[3] > tup_b[3]:
        return tup_a
    if tup_a[3] < tup_b[3]:
        return tup_b

    return tup_a


# 查询指定项目的所有版本号
def __get_version_list(artifact_id, group_id, url, cookie):
    # 设置分页查询的参数
    page_index = 1
    page_size = 300
    request_dist = __build_request_dist(artifact_id, group_id, page_index, page_size)
    response = __post_json(request_dist, url, cookie)

    # 获取版本号的总数量、版本号列表
    total = __get_total(response)
    version_list = []
    # 从响应参数中，提取出所有版本号，并追加至数组
    __fill_version(version_list, response)

    # 计算剩余的循环次数
    # 即，向上取整(总数/页大小)-1
    circulation_num = math.ceil(total / page_size) - 1

    while circulation_num > 0:
        # 循环分页查询版本号
        circulation_num -= 1
        page_index += 1
        request_dist = __build_request_dist(artifact_id, group_id, page_index, page_size)
        response = __post_json(request_dist, url, cookie)

        # 从响应参数中，提取出所有版本号，并追加至数组
        __fill_version(version_list, response)

    return version_list


# 获取版本号的总数量
def __get_total(response):
    response = json.loads(response)
    result = response["result"]
    total = result["total"]
    return total


# 从响应参数中，提取出所有版本号，并追加至数组
def __fill_version(version_list, response):
    response = json.loads(response)
    result = response["result"]
    data = result["data"]
    for i in data:
        version_list.append(i['version'])
    return version_list


# 构建请求参数
def __build_request_dist(artifact_id, group_id, page_index, page_size):
    # 设置起始值
    start = (page_index - 1) * page_size

    # 查询参数
    request_dist = {
        'action': 'coreui_Search',
        'method': 'read',
        'data': [
            {
                'page': page_index,
                'start': start,
                'limit': page_size,
                'filter': [
                    # 以maven的格式搜索
                    {
                        'property': 'format',
                        'value': 'maven2'
                    },
                    {
                        'property': 'attributes.maven2.artifactId',
                        'value': artifact_id
                    },
                    {
                        'property': 'attributes.maven2.groupId',
                        'value': group_id
                    },
                    # 只查询release版本
                    {
                        'property': 'repository_name',
                        'value': 'maven-releases'
                    }
                ]
            }
        ],
        'type': 'rpc',
        'tid': 14
    }
    return request_dist


# json格式的post请求
def __post_json(request_dist, url, cookie):
    # 将数据转为JSON格式
    data_json = json.dumps(request_dist)

    headers = {'Cookie': cookie, 'content-type': 'application/json', 'charset': 'utf-8'}
    username = "dev"
    password = "dev"
    response = requests.post(url, data=data_json.encode('utf-8'), headers=headers, auth=(username, password))
    return response.text


if __name__ == '__main__':
    main()