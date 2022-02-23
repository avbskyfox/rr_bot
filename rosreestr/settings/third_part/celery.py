import environ

env = environ.Env()


CELERY_BROKER_URL = env('CELERY_REDIS_URL')
