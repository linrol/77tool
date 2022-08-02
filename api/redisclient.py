import redis
class RedisClient(object):
    def __init__(self):
        self.pool = redis.ConnectionPool(host = "linrol.cn", port = 6379,
                                         password = 'linrol_redis',db=0,
                                         decode_responses=True, max_connections=16)
    def get_connection(self):
        return redis.Redis(connection_pool = self.pool)

redisClient = RedisClient()

def add_mr(key, mr_id):
    mr_ids = get_mr_ids(key)
    if mr_ids is None:
        redisClient.get_connection().hmset("q7link-mr-log", {key: mr_id})
    else:
        redisClient.get_connection().hmset("q7link-mr-log", {key: mr_ids + "," + mr_id})

def get_mr_ids(key):
    return redisClient.get_connection().hget("q7link-mr-log", key)

def delete_mr(key):
    redisClient.get_connection().hdel("q7link-mr-log", key)