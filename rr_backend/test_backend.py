from unittest import TestCase
from rr_backend.backend import Backend
from loguru import logger
import asyncio

address_list = ['Балаково харьковская 23', 'Балаково ленина 2']
numbers_list = ['']


class TestBackend(TestCase):
    def test_find_adress(self):
        loop = asyncio.get_event_loop()
        for address in address_list:
            result = loop.run_until_complete(Backend.async_find_adress(address))
            for item in result:
                self.assertIn('value', item)
                self.assertIn('data', item)
    #
    # def test_objects_by_address(self):
    #     self.fail()
    #
    # def test_object_by_number(self):
    #     self.fail()
