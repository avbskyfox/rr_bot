import requests
import aiohttp
import os
from loguru import logger
import asyncio
from yarl import URL
import json

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

# options = webdriver.ChromeOptions()
# options.add_argument('headless')
# driver = webdriver.Chrome(options=options, executable_path = '/usr/local/bin/chromedriver')

TOKEN = os.environ.get('BASE-N_TOKEN')
APIEGRN_TOKEN = os.environ.get('APIEGRN_TOKEN')
BASE_URL = 'https://api-rosreestr.base-n.ru/rosreestr/api/'
GET_BY_CADNUM_URL = 'get_by_cadnum/'
SEARCH_BY_ADDRESS_URL = 'search_by_address/'
CHECK_BASE_N_DEPOSIT_URL = 'check_base_n_deposit/'
RR_URL = 'http://rosreestr.gov.ru/api/online/fir_objects/'


class BasenClient:
    @staticmethod
    async def get_info(cadnum: str):
        payload = {'base_n_api_key': TOKEN, 'cadnum': cadnum}
        url = BASE_URL + GET_BY_CADNUM_URL
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return await response.json()

    @staticmethod
    async def check_basen_deposit():
        payload = {'base_n_api_key': TOKEN}
        url = BASE_URL + CHECK_BASE_N_DEPOSIT_URL
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                return await response.json()

    def get_doc_type1(self, query):
        pass

    def get_doc_type2(self, query):
        pass


