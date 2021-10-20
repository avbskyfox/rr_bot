import pickle

from django.conf import settings
from loguru import logger
from redis import Redis

redis = Redis(host=settings.CACHING_MIDDLEWARE_REDIS_HOST,
              port=settings.CACHING_MIDDLEWARE_REDIS_PORT,
              db=settings.CACHING_MIDDLEWARE_REDIS_DB)

cash_ttl = settings.CASH_TTL


def cached_call(method, ttl=cash_ttl):
    def wraper(*args, **kwargs):
        key_str = pickle.dumps({'args': args, 'kwargs': kwargs})
        # logger.debug(f'cashed key len: {len(key_str)}')
        redis_key = key_str
        cached_data = redis.get(redis_key)
        if cached_data:
            return pickle.loads(cached_data)
        else:
            returned_value = method(*args, **kwargs)
            redis.set(redis_key, pickle.dumps(returned_value), ex=ttl)
            return returned_value

    return wraper


def async_cashed_call(method, ttl=cash_ttl):
    async def wraper(*args, **kwargs):
        key_str = pickle.dumps({'args': args, 'kwargs': kwargs})
        # logger.debug(f'cashed key len: {len(key_str)}')
        redis_key = key_str
        # redis.delete(redis_key)
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
