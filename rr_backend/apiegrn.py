import json

import aiohttp
from django.conf import settings

APIEGRN_TOKEN = settings.APIEGRN_TOKEN
SEARCH_URL = 'https://apiegrn.ru/api/cadaster/search'
INFO_URL = 'https://apiegrn.ru/api/cadaster/objectInfoFull'


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
                return await response.json()

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
                return json.loads(text)
