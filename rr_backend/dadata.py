import aiohttp
import os
from loguru import logger
import asyncio


DADATA_TOKEN = os.environ.get('DADATA_TOKEN')
DADATA_URL = 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address'


class DadataClient:
    @staticmethod
    async def find_address(addr_string: str):
        headers = {'Authorization': f'Token {DADATA_TOKEN}'}
        async with aiohttp.ClientSession() as session:
            async with session.post(DADATA_URL, json={'query': addr_string}, headers=headers) as response:
                variants = await response.json()
                return variants['suggestions']
