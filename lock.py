from time import sleep
from redis import Redis
from loguru import logger

from redis.lock import Lock


sleep_time = 3
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
        self.try_to_acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def locked(self):
        val = self.redis.get(self.name)
        logger.debug(f'key: {self.name},val: {val}')
        if val is not None:
            return True
        else:
            return False

    def acquire(self):
        self.redis.set(self.name, 'lock', ex=self.timeout)

    def try_to_acquire(self):
        logger.debug(f'Try to acquire lock named {self.name}')
        while self.locked():
            sleep(sleep_time)
        self.acquire()

    def release(self):
        self.redis.delete(self.name)
