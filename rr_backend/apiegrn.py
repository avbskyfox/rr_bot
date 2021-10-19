import json

import aiohttp
from django.conf import settings
from loguru import logger

from rr_backend.rosreestr import NotFound

APIEGRN_TOKEN = settings.APIEGRN_TOKEN
# APIEGRN_TOKEN = 'PXN3-L0OV-IE7C-A1FZ'
SEARCH_URL = 'https://apiegrn.ru/api/cadaster/search'
INFO_URL = 'https://apiegrn.ru/api/cadaster/objectInfoFull'


def _get_from(details: dict, key_string):
    for key, value in details.items():
        if key_string in key:
            return value
        else:
            continue
    return None


class ApiEgrnClient:
    @staticmethod
    async def search(address: str):
        headers = {'Token': APIEGRN_TOKEN}
        data = {
            'mode': 'normal',
            'query': address
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(SEARCH_URL, json=data, headers=headers) as response:
                result = await response.json()
                logger.debug(f'api_egrn: {result}')
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
