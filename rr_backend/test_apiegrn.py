from django.test import TestCase
from asgiref.sync import async_to_sync
from asyncio import run
from rr_backend.apiegrn import ApiEgrnClient
from loguru import logger

addr_list = [
    'г Екатеринбург, ул Машинная, д 31В, кв 107',
    'г Пермь, ул Таганрогская, д 107, кв 36',
]


@async_to_sync
async def search(address):
    return await ApiEgrnClient.search(address)


class TestApiEgrnClient(TestCase):
    def test_search(self):
        for addr in addr_list:
            result = search(addr)
            print(result)

    def test_account_info(self):
        response = run(ApiEgrnClient.account_info())
        logger.debug(response)
