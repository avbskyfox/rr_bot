from time import sleep
from redis import Redis

sleep_time = 0.1
store_value = True
name_prefix = 'masBT5cavaud3265dvk'


class RedisLock:
    """
    Very simple implementation of lock, used Redis to store locks
    """
    def __init__(self, redis: Redis, name: str, timeout: int = 0):
        """
        @type redis: Redis instance
        @type name: str name of the lock
        @type timeout: int time to live of the lock
        """
        self.redis = redis
        self.name = f'{name_prefix}-{name}'
        self.timeout = timeout
        self.sleep_time = sleep_time

    def __enter__(self):
        value = 'lock'
        while value == 'lock':
            value = self.redis.get(self.name)
            if value == 'lock':
                sleep(sleep_time)
        self.redis.set(self.name, 'lock', ex=self.timeout)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.redis.delete(self.name)
