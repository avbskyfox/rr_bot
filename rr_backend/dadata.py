import aiohttp
import requests
from django.conf import settings
import json

DADATA_TOKEN = settings.DADATA_TOKEN
DADATA_URL = 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address'


class DadataClient:
    @staticmethod
    async def async_find_address(addr_string: str):
        headers = {'Authorization': f'Token {DADATA_TOKEN}'}
        async with aiohttp.ClientSession() as session:
            async with session.post(DADATA_URL, json={'query': addr_string}, headers=headers) as response:
                variants = await response.json()
                with open('variants', 'w') as f:
                    json.dump(variants, f, ensure_ascii=False, indent=3)
                return variants['suggestions']

    @staticmethod
    def find_address(addr_string: str):
        headers = {'Authorization': f'Token {DADATA_TOKEN}'}
        response = requests.post(DADATA_URL, json={'query': addr_string}, headers=headers)
        return response.json()['suggestions']