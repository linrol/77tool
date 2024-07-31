import os
import json
import redis


class RedisClient(object):
    def __init__(self):
        self.password = os.environ.get("REDIS_PASSWORD")
        self.pool = redis.ConnectionPool(host="redis", port=6379,
                                         password=self.password, db=2,
                                         decode_responses=True,
                                         max_connections=16)

    def __del__(self):
        self.get_connection().close()

    def get_connection(self):
        return redis.Redis(connection_pool=self.pool)


redisClient = RedisClient()


def hmset(name, mapping):
    redisClient.get_connection().hmset(name, mapping)


def hget_default(name, key, default):
    v = hget(name, key)
    if v is None:
        return default
    return v


def hget(name, key):
    return redisClient.get_connection().hget(name, key)


def hgetall(name):
    return redisClient.get_connection().hgetall(name)


def hget_key(name, v):
    kvs = redisClient.get_connection().hgetall(name)
    for key, value in kvs.items():
        if value == v:
            return key
    return None


def hdel(name, key):
    redisClient.get_connection().hdel(name, key)


def append(name, key, value):
    connection = redisClient.get_connection()
    has_value = hget(name, key)
    if has_value is not None:
        value = ",".join(set((value + "," + has_value).split(",")))
    connection.hmset(name, {key: value})
    return len(list(filter(lambda c: c not in ['宁夏生产global集群', ''], value.split(","))))


def duplicate_msg(msg):
    msg_id = msg.get('MsgId')
    if msg_id is None:
        return False
    connection = redisClient.get_connection()
    is_accept = connection.hexists("q7link-msg-log", msg_id)
    if not is_accept:
        connection.hmset("q7link-msg-log", {msg_id: json.dumps(msg)})
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


def save_user_task(key, value):
    redisClient.get_connection().hmset("q7link-user-task", {key: value})


def save_task_depend(key, value):
    redisClient.get_connection().hmset("q7link-task-depend", {key: value})


def get_user_task(key):
    return redisClient.get_connection().hget("q7link-user-task", key)


def get_branch_mapping():
    return redisClient.get_connection().hgetall("q7link-branch-mapping")


def get_version():
    return redisClient.get_connection().get("q7link-branch-manage-version")
