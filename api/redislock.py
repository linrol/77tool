import os
import socket
import threading
import time


class RedisLock:
    """
    分布式锁
    """

    def __init__(self, redis_conn, Django=False):
        """

        @param redis_conn: redis 实例对象
        @param Django: 是否是django，如果是django框架就使用django自带缓存
        @type Django: bool
        """
        self.redis_conn = redis_conn
        self.ip = socket.gethostbyname(socket.gethostname())
        self.pid = os.getpid()
        self.sentinel = object()
        self.django = Django

    @staticmethod
    def get_lock_key(key: str) -> str:
        """
        格式化锁名称
        @param key: 名称
        @type key: str
        @return: key 名称
        @rtype: str
        """
        lock_key = f'lock_{key}'
        return lock_key

    def gen_unique_value(self) -> str:
        """
        获取锁value使锁有唯一性，防止其它线程误删
        @return:
        @rtype:
        """
        thread_name = threading.current_thread().name
        time_now = time.time()
        unique_value = f'{self.ip}-{self.pid}-{thread_name}-{time_now}'
        return unique_value

    def get_lock(self, key, timeout: int = 100) -> str:
        """
        获取锁
        @param key: 锁名
        @type key: str
        @param timeout: 锁过期时间，防止死锁
        @type timeout: int
        @return:
        @rtype: str
        """

        lock_key = self.get_lock_key(key)
        unique_value = self.gen_unique_value()
        while True:
            if self.django:
                judge = self.redis_conn.add(lock_key, unique_value, timeout)
            else:
                judge = self.redis_conn.set(lock_key, unique_value, nx=True, ex=timeout)
            if judge:
                return unique_value
            time.sleep(0.001)


    def del_lock(self, key, value):
        # 释放锁
        lock_key = self.get_lock_key(key)
        old_lock_value = self.redis_conn.get(lock_key)
        if old_lock_value == value:
            return self.redis_conn.delete(lock_key)