import asyncio

import aiohttp
from loguru import logger
from yarl import URL
from django.conf import settings
SSL_VERIFY = settings.SSL_VERIFY

timeout = aiohttp.ClientTimeout(total=15)


class NotFound(Exception):
    pass


class TemporaryUnavalible(Exception):
    pass


class RosreestrClient:
    @classmethod
    async def find_objects(cls, dadata):
        try:
            return await cls._find_objects(dadata)
        except asyncio.TimeoutError:
            raise TemporaryUnavalible

    @classmethod
    async def _find_objects(cls, dadata):
        url = 'https://rosreestr.ru/api/online/address/fir_objects'
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            params = await cls._get_settl(session, dadata)
            params['street'] = str(dadata['data']['street'])
            params['house'] = dadata['data']['house']
            if dadata['data']['flat']:
                params['apartment'] = dadata['data']['flat']
            if dadata['data']['block']:
                params['building'] = dadata['data']['block']
            url += '?'
            for key, value in params.items():
                url += f'&{key}={value}'

            async with session.get(URL(url, encoded=False), ssl=SSL_VERIFY) as response:
                if response.status == 204:
                    raise NotFound
                js = await response.json()
        logger.debug(js)
        return js

    @classmethod
    async def _get_reg(cls, session: aiohttp.ClientSession, dadata_query):
        query = dadata_query['data']['city'] or dadata_query['data']['area']
        macro_reg = await cls._get_macro_reg(session, dadata_query)
        async with session.get(f'https://rosreestr.ru/api/online/regions/{macro_reg}', ssl=SSL_VERIFY) as response:
            data = await response.json()
            for item in data:
                if query.lower() in item['name'].lower():
                    return {'macroRegionId': macro_reg, 'regionId': item['id']}
            return query

    @classmethod
    async def _get_settl(cls, session: aiohttp.ClientSession, dadata_query):
        query = dadata_query['data']['city'] or dadata_query['data']['settlement']
        reg = await cls._get_reg(session, dadata_query)
        async with session.get(f'https://rosreestr.ru/api/online/regions/{reg["regionId"]}', ssl=SSL_VERIFY) as respone:
            data = await respone.json()
            for item in data:
                if query.lower() in item['name'].lower():
                    # reg['settlementId'] = item['id']
                    return reg
            raise NotFound

    @staticmethod
    async def _get_macro_reg(session: aiohttp.ClientSession, dadata_query):
        query = dadata_query['data']['region']
        query = query.replace('Респ', '')
        query = query.replace('/Якутия/', '')
        query = query.strip()
        async with session.get('https://rosreestr.gov.ru/api/online/macro_regions', ssl=SSL_VERIFY) as response:
            data = await response.json()
            for item in data:
                if query.lower() in item['name'].lower():
                    return item['id']
            return query
