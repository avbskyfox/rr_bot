import json
import os.path

from django.test import TestCase
from asgiref.sync import async_to_sync
from asyncio import run
from rr_backend.apiegrn import ApiEgrnClient, SELF_CHECK_FILE, SEARCHES_BEFORE_CHECK
from loguru import logger

addr_list = [
    'г Екатеринбург, ул Машинная, д 31В, кв 107',
]


@async_to_sync
async def search(address):
    return await ApiEgrnClient.search(address)


class TestApiEgrnClient(TestCase):
    def test_search(self):
        try:
            os.remove(SELF_CHECK_FILE)
        except FileNotFoundError:
            pass
        for addr in addr_list:
            result = search(addr)
            print(result)
        if not os.path.exists(SELF_CHECK_FILE):
            self.fail(f'Не создан файл селф чека {SELF_CHECK_FILE}')

    def test_account_info(self):
        response = run(ApiEgrnClient.account_info())
        logger.debug(response)

    def test_check(self):
        try:
            os.remove(SELF_CHECK_FILE)
        except FileNotFoundError:
            pass
        run(ApiEgrnClient.check())
        if not os.path.exists(SELF_CHECK_FILE):
            self.fail(f'Не создан файл селф чека {SELF_CHECK_FILE}')
        run(ApiEgrnClient.check())
        with open(SELF_CHECK_FILE, 'r') as f:
            data = json.load(f)
        self.assertEqual(data['searches_before_check'], SEARCHES_BEFORE_CHECK - 1)
        data['searches_before_check'] = 0
        with open(SELF_CHECK_FILE, 'w') as f:
            json.dump(data, f)
        run(ApiEgrnClient.check())
        with open(SELF_CHECK_FILE, 'r') as f:
            data = json.load(f)
        self.assertEqual(data['searches_before_check'], SEARCHES_BEFORE_CHECK)

