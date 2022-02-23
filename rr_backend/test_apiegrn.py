from django.test import TestCase
from asgiref.sync import async_to_sync
import os
import django
#
#
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rosreestr.settings')
# django.setup()
from rr_backend.apiegrn import ApiEgrnClient

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
