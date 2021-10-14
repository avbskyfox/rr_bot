from django.conf import settings
from redis import Redis
import json
from loguru import logger
import zlib
import pickle


redis = Redis(host=settings.CACHING_MIDDLEWARE_REDIS_HOST,
              port=settings.CACHING_MIDDLEWARE_REDIS_PORT,
              db=settings.CACHING_MIDDLEWARE_REDIS_DB)


def cached_call(method, ttl=86400):
    def wraper(*args, **kwargs):
        key_str = pickle.dumps({'args': args, 'kwargs': kwargs})
        logger.debug(f'cashed key len: {len(key_str)}')
        redis_key = key_str
        cached_data = redis.get(redis_key)
        if cached_data:
            return pickle.loads(cached_data)
        else:
            returned_value = method(*args, **kwargs)
            redis.set(redis_key, pickle.dumps(returned_value), ex=ttl)
            return returned_value
    return wraper


def async_cashed_call(method, ttl=86400):
    async def wraper(*args, **kwargs):
        key_str = pickle.dumps({'args': args, 'kwargs': kwargs})
        logger.debug(f'cashed key len: {len(key_str)}')
        redis_key = key_str
        cached_data = redis.get(redis_key)
        if cached_data:
            logger.debug('values restored from cash')
            return pickle.loads(cached_data)
        else:
            returned_value = await method(*args, **kwargs)
            redis.set(redis_key, pickle.dumps(returned_value), ex=ttl)
            logger.debug('values saved to cash')
            return returned_value
    return wraper
