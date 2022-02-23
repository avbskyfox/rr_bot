import aiohttp
import requests
from django.conf import settings
from loguru import logger

TOKEN = settings.BASE_N_TOKEN
APIEGRN_TOKEN = settings.APIEGRN_TOKEN
FGIS_EGRN_TOKEN = settings.FGIS_EGRN_TOKEN

BASE_URL = 'https://api-rosreestr.base-n.ru/rosreestr/api/'
GET_BY_CADNUM_URL = 'get_by_cadnum/'
SEARCH_BY_ADDRESS_URL = 'search_by_address/'
CHECK_BASE_N_DEPOSIT_URL = 'check_base_n_deposit/'
CHECK_ORDER_URL = 'check_order_status/'
GET_EXCERPT = 'get_extruct/'
ORDER_URL = 'order_extruct/'


class BasenClient:
    @staticmethod
    async def async_get_info(cadnum: str):
        payload = {'base_n_api_key': TOKEN, 'cadnum': cadnum}
        url = BASE_URL + GET_BY_CADNUM_URL
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return await response.json()

    @staticmethod
    async def async_check_basen_deposit():
        payload = {'base_n_api_key': TOKEN}
        url = BASE_URL + CHECK_BASE_N_DEPOSIT_URL
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return await response.json()

    @staticmethod
    def check_basen_deposit():
        payload = {'base_n_api_key': TOKEN}
        url = BASE_URL + CHECK_BASE_N_DEPOSIT_URL
        return requests.post(url, json=payload).json()

    @classmethod
    def order_docs(cls, cadnum: str, doc_type: str):
        logger.debug(f'base_n: {cls.check_basen_deposit()}')
        payload = {
            'base_n_api_key': TOKEN,
            'fgis_egrn_key': FGIS_EGRN_TOKEN,
            'cadnum': cadnum,
            'document_type': doc_type
        }
        url = BASE_URL + ORDER_URL
        response = requests.post(url, json=payload)
        data = response.json()
        if response.status_code == 200 and data['message'] == 'ok':
            return {'success': True, 'number': data['query_num'], 'raw': data}
        else:
            return {'success': False, 'message': f"{data['error_message']}: {data['description']}", 'raw': data}

    @staticmethod
    def check_status(query_num):
        payload = {
            'base_n_api_key': TOKEN,
            'fgis_egrn_key': FGIS_EGRN_TOKEN,
            'query_num': query_num,
        }
        url = BASE_URL + CHECK_ORDER_URL
        response = requests.post(url, json=payload)
        data = response.json()
        logger.debug(f'base_n: {data}')
        return data

    @staticmethod
    async def async_check_status(query_num):
        payload = {
            'base_n_api_key': TOKEN,
            'fgis_egrn_key': FGIS_EGRN_TOKEN,
            'query_num': query_num,
        }
        url = BASE_URL + CHECK_ORDER_URL
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return await response.json()

    @staticmethod
    def get_excerpt(query_num, doc_format='pdf'):
        payload = {
            'base_n_api_key': TOKEN,
            'fgis_egrn_key': FGIS_EGRN_TOKEN,
            'query_num': query_num,
            'format': doc_format,
        }
        url = BASE_URL + GET_EXCERPT
        response = requests.post(url, json=payload)
        data = response.content
        logger.debug(f'base_n get_docs status code: {response.status_code}')
        return data


def get_type1(**kwargs):
    cadnum = kwargs.get('number')
    return BasenClient.order_docs(cadnum, 'object_info')


def get_type2(**kwargs):
    cadnum = kwargs.get('number')
    return BasenClient.order_docs(cadnum, 'ownership')


def check_excerpt_status(query_num):
    return BasenClient.check_status(query_num)
