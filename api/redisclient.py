import json
import redis


class RedisClient(object):
    def __init__(self):
        self.pool = redis.ConnectionPool(host="linrol.cn", port=6379,
                                         password='linrol_redis', db=2,
                                         decode_responses=True,
                                         max_connections=16)

    def __del__(self):
        self.get_connection().close()

    def get_connection(self):
        return redis.Redis(connection_pool=self.pool)


redisClient = RedisClient()


def hmset(name, mapping):
    redisClient.get_connection().hmset(name, mapping)


def hget(name, key):
    return redisClient.get_connection().hget(name, key)


def duplicate_msg(msg):
    msg_id = msg.get('MsgId')
    if msg_id is None:
        return False
    connection = redisClient.get_connection()
    is_accept = connection.hexists("crop-msg-log", msg_id)
    if not is_accept:
        connection.hmset("crop-msg-log", {msg_id: json.dumps(msg)})
    return is_accept


def duplicate_correct_id(correct_id, branch, project):
    if correct_id is None:
        return False
    connection = redisClient.get_connection()
    is_accept = connection.hexists("q7link-branch-correct-log", correct_id)
    if not is_accept:
        content = branch + project
        connection.hmset("q7link-branch-correct-log", {correct_id: content})
    return is_accept


def add_mr(key, mr_id):
    connection = redisClient.get_connection()
    mr_ids = get_mr_ids(key)
    if mr_ids is None:
        connection.hmset("q7link-mr-log", {key: mr_id})
    else:
        connection.hmset("q7link-mr-log", {key: mr_ids + "," + mr_id})


def get_mr_ids(key):
    return redisClient.get_connection().hget("q7link-mr-log", key)


def delete_mr(key):
    redisClient.get_connection().hdel("q7link-mr-log", key)


def get_user_id(chines_name):
    if chines_name is None or chines_name == '':
        return chines_name
    user_id = redisClient.get_connection().hget("q7link-git-user", chines_name)
    return chines_name if user_id is None else user_id


def save_create_branch_task(key, value):
    redisClient.get_connection().hmset("q7link-user-task", {key: value})


def get_create_branch_task(key):
    return redisClient.get_connection().hget("q7link-user-task", key)


def get_branch_mapping():
    return redisClient.get_connection().hgetall("q7link-branch-mapping")
