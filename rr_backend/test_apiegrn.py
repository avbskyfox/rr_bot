from unittest import TestCase
from rr_backend.apiegrn import ApiEgrnClient
from asgiref.sync import async_to_sync



addr = 'г Екатеринбург, ул Машинная, д 31В, кв 107'


@async_to_sync
async def search(address):
    return await ApiEgrnClient.search(address)


class TestApiEgrnClient(TestCase):
    def test_search(self):
        result = search(addr)
        print(result)
