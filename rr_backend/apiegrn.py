import json

import aiohttp
from django.conf import settings
from django.utils import timezone
from loguru import logger
import os

from rr_backend.rosreestr import NotFound, TemporaryUnavalible

APIEGRN_TOKEN = settings.APIEGRN_TOKEN
# APIEGRN_TOKEN = 'PXN3-L0OV-IE7C-A1FZ'
SEARCH_URL = 'https://apiegrn.ru/api/cadaster/search'
INFO_URL = 'https://apiegrn.ru/api/cadaster/objectInfoFull'
ACCOUNT_URL = 'https://apiegrn.ru/api/account/info'

SELF_CHECK_FILE = 'apiegrn_selfcheck.json'
SEARCH_COST = 2
ALARM_BALANCE = 100
ALARM_FREE_COUNT = 50
SEARCHES_BEFORE_CHECK = 10


def _get_from(details: dict, key_string):
    for key, value in details.items():
        if key_string in key:
            return value
        else:
            continue
    return None


class ApiEgrnClient:
    @classmethod
    async def search(cls, address: str):
        await cls.check()
        headers = {'Token': APIEGRN_TOKEN}
        data = {
            'mode': 'normal',
            'query': address
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(SEARCH_URL, json=data, headers=headers) as response:
                result = await response.json()
                logger.debug(f'api_egrn: {result}')
                if result['error'] == {'code': 503, 'mess': 'Rosreestr is temporarily unavailable'}:
                    raise TemporaryUnavalible('result')
                return [{'nobjectCn': item['CADNOMER'], 'addressNotes': item['ADDRESS']} for
                        item in result['objects']]

    @staticmethod
    async def get_info(cadnum: str):
        headers = {'Token': APIEGRN_TOKEN}
        data = {
            'deep': 0,
            'query': cadnum
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(INFO_URL, json=data, headers=headers) as response:
                text = await response.text()
                variant = json.loads(text)
                logger.debug(variant)
                if variant['error']:
                    if variant['error']['code'] == 'OBJECT_NOT_FOUND':
                        raise NotFound
                if variant['EGRN'].get('rights'):
                    limits = 'Зафиксированы' if len(variant['EGRN']['rights'][0].get('limits', [])) > 0 else 'Не зафиксированы'
                else:
                    limits = '-'
                output = {
                    'Кадастровый номер': _get_from(variant['EGRN']['details'], 'Кадастровый') or '',
                    'Статус объекта': _get_from(variant['EGRN']['details'], 'Статус') or '',
                    'Адрес': variant["EGRN"]["object"].get("ADDRESS") or '',
                    'Объект': f"{_get_from(variant['EGRN']['details'], 'Тип') or 'Не определено'} "
                              f"({_get_from(variant['EGRN']['details'], 'Этажность') or '-'} эт.)",
                    # 'Год ввода': variant['EGRN']['details']['Кадастровый номер'] or ''
                    'Кадастровая стоимость': f"{_get_from(variant['EGRN']['details'], 'стоимость') or '-'} "
                                             f"({_get_from(variant['EGRN']['details'], 'Дата внесения стоимости') or '--.--.--'} г.)",
                    'Площадь': _get_from(variant['EGRN']['details'], 'Площадь') or '',
                    'Количество правообладателей': _get_from(variant['EGRN']['details'],
                                                             'Количество правообладателей') or '0',
                    'Вид собственности': f"{variant['EGRN']['rights'][0]['type']} (от {variant['EGRN']['rights'][0]['date'] or ''} г.)" if
                    variant['EGRN']['rights'] else 'незвестно',
                    'Обременения': limits
                }
                logger.debug(output)
                return output

    @staticmethod
    async def account_info():
        headers = {'Token': APIEGRN_TOKEN}
        async with aiohttp.ClientSession() as session:
            async with session.get(ACCOUNT_URL, headers=headers) as response:
                return await response.json()

    @classmethod
    async def check(cls):
        if not os.path.exists('apiegrn_selfcheck.json'):
            await cls._dump_account_info()
        else:
            with open(SELF_CHECK_FILE, 'r') as f:
                data = json.load(f)
            if data['searches_before_check'] <= 0:
                await cls._dump_account_info()
            else:
                new_data = {
                    'free_search': data['free_search'] - 1,
                    'balance': data['balance'] - SEARCH_COST,
                    'searches_before_check': data['searches_before_check'] - 1
                }
                with open(SELF_CHECK_FILE, 'w') as f:
                    json.dump(new_data, f)

    @classmethod
    async def _dump_account_info(cls):
        info = await cls.account_info()
        data = {
            'free_search': info['tariff']['search_limit']['free'],
            'balance': info['balance'],
            'searches_before_check': SEARCHES_BEFORE_CHECK
        }
        if data['free_search'] <= ALARM_FREE_COUNT or data['balance'] <= ALARM_BALANCE:
            from rr_telebot.tasks import send_to_adm_group
            send_to_adm_group.delay(f'API EGRN баланс: {data["balance"]}\n'
                                    f'количество бесплатных поисков: {data["free_search"]}')
        with open(SELF_CHECK_FILE, 'w') as f:
            json.dump(data, f)
