from django.test import TestCase
from rr_backend.basen import BasenClient
from loguru import logger


class TestBasenClient(TestCase):
    def test_check_basen_deposit(self):
        response = BasenClient.check_basen_deposit()
        logger.debug(f'current deposit: {response}')
        self.assertIsInstance(response, int)
