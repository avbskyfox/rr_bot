import aiohttp
import os
from loguru import logger
import asyncio
import json
from yarl import URL


class RosreestrClient:
    @classmethod
    async def find_objects(cls, dadata):
        url = 'http://rosreestr.ru/api/online/address/fir_objects'
        logger.debug(dadata)
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as session:
            params = await cls._get_settl(session, dadata)
            params['street'] = dadata['data']['street']
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

            async with session.get(URL(url, encoded=True)) as response:
                logger.debug(response.request_info)
                logger.debug(await response.text())
                logger.debug(response.status)
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
        query = dadata_query['data']['settlement'] or dadata_query['data']['city']
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
            return query

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
