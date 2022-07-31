from redis import Redis, ConnectionPool

# 连接池
redis_pool = ConnectionPool(host="linrol.cn", port=6379,
                            password="linrol_redis", db=0,
                            decode_responses=True, max_connections=16)
client = Redis(connection_pool=redis_pool)

def add_mr(key, mr_id):
    mr_ids = get_mr_ids(key)
    if mr_ids is None:
        client.hmset("q7link-mr-log", {key: mr_id})
    else:
        client.hmset("q7link-mr-log", {key: mr_ids + "," + mr_id})

def get_mr_ids(key):
    return client.hget("q7link-mr-log", key)

def delete_mr(key):
    client.hdel("q7link-mr-log", key)