from unittest import TestCase
from django.conf import settings

from misc import generate_token


class Test(TestCase):
    def test_generate_token(self):
        token = generate_token({'key1': 'val1', 'key2': 'val2', 'Shops': 'unwanted_val'})
        self.assertEqual(64, len(token))


class Test(TestCase):
    def test_create_payment(self):
        params = {
            "TerminalKey": settings.TINKOFF_TERMINAL,
            "Amount": "100",
            "OrderId": "1",
            "Description": "Тестовый платеж",
            "Receipt": {
                "Email": "a@test.ru",
                "Phone": "+79031234567",
                "EmailCompany": "b@test.ru",
                "Taxation": "osn",
                "Items": [
                    {
                        "Name": "Наименование товара 1",
                        "Price": 100,
                        "Quantity": 1.00,
                        "Amount": 100,
                        "PaymentMethod": "full_prepayment",
                        "PaymentObject": "service",
                        "Tax": "vat10"
                    }
                ]
            }
        }
