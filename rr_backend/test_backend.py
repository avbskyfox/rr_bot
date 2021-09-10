from django.test import TestCase
# from unittest import TestCase
from rr_backend.backend import Backend
from loguru import logger
import asyncio
from rr_backend.basen import BasenClient


address_list = ['г Иркутск, мкр Лесной, ул Педагогическая, д 32']
numbers_list = ['']


class TestBackend(TestCase):
    def test_find_adress(self):
        loop = asyncio.get_event_loop()
        for address in address_list:
            result = loop.run_until_complete(Backend.async_find_adress(address))
            logger.debug(result)
            for item in result:
                self.assertIn('value', item)
                self.assertIn('data', item)
    #
    # def test_objects_by_address(self):
    #     self.fail()
    #
    # def test_object_by_number(self):
    #     self.fail()

    def test_get_excerpt(self):
        query_num = '53b4e764-b7f0-dc81-a731-9b5a83dc41dfa5fc0316'
        data = BasenClient.get_excerpt(query_num)
        logger.debug(data)
        with open('excerpt2.pdf', 'wb') as f:
            f.write(data)
