import asyncio
import json

import aiohttp
from loguru import logger
from yarl import URL


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
        url = 'http://rosreestr.ru/api/online/address/fir_objects'
        logger.debug(dadata)
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            params = await cls._get_settl(session, dadata)
            logger.debug(params)
            params['street'] = str(dadata['data']['street'])
            params['house'] = dadata['data']['house']
            if dadata['data']['flat']:
                params['apartment'] = dadata['data']['flat']
            if dadata['data']['block']:
                params['building'] = dadata['data']['block']

            logger.debug(params)
            url += '?'
            for key, value in params.items():
                url += f'&{key}={value}'
            logger.debug(url)

            async with session.get(URL(url, encoded=False)) as response:
                logger.debug(response.request_info)
                logger.debug(await response.text())
                logger.debug(response.status)
                if response.status == 204:
                    raise NotFound
                js = await response.json()
                result = json.dumps(js, ensure_ascii=False, indent=3)
                logger.debug(result)
        return js

    @classmethod
    async def _get_reg(cls, session: aiohttp.ClientSession, dadata_query):
        query = dadata_query['data']['city'] or dadata_query['data']['area']
        logger.debug(query)
        macro_reg = await cls._get_macro_reg(session, dadata_query)
        async with session.get(f'http://rosreestr.ru/api/online/regions/{macro_reg}') as respone:
            data = await respone.json()
            for item in data:
                if query.lower() in item['name'].lower():
                    logger.debug(item)
                    return {'macroRegionId': macro_reg, 'regionId': item['id']}
            return query

    @classmethod
    async def _get_settl(cls, session: aiohttp.ClientSession, dadata_query):
        query = dadata_query['data']['city'] or dadata_query['data']['settlement']
        logger.debug(query)
        reg = await cls._get_reg(session, dadata_query)
        async with session.get(f'http://rosreestr.ru/api/online/regions/{reg["regionId"]}') as respone:
            data = await respone.json()
            logger.debug(data)
            for item in data:
                if query.lower() in item['name'].lower():
                    logger.debug(item)
                    # reg['settlementId'] = item['id']
                    return reg
            raise NotFound

    @staticmethod
    async def _get_macro_reg(session: aiohttp.ClientSession, dadata_query):
        query = dadata_query['data']['region']
        query = query.replace('Респ', '')
        query = query.replace('/Якутия/', '')
        query = query.strip()
        async with session.get('http://rosreestr.gov.ru/api/online/macro_regions') as respone:
            data = await respone.json()
            for item in data:
                if query.lower() in item['name'].lower():
                    logger.debug(item)
                    return item['id']
            return query
