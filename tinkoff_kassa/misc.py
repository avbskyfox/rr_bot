from hashlib import sha256
from tinkoff_kassa.tinkoff_urls import *
from django.conf import settings
from loguru import logger


def generate_token(request: dict):
    copy = {key.lower(): request[key] for key in request.keys()}
    copy['password'] = settings.TINKOFF_PASSWORD
    unwanted_keys = ['shops', 'receipt', 'data']
    keys = list(copy.keys())
    keys.sort()
    values_str = ''
    for key in keys:
        if key in unwanted_keys:
            continue
        if isinstance(copy[key], bool):
            copy[key] = str(copy[key]).lower()
        values_str += str(copy[key])
    return sha256(values_str.encode()).hexdigest()


def create_payment(params: dict):
    pass
