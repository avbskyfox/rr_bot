import random

from django.test import TestCase

from tinkoff_kassa.models import PaymentModel

from django.contrib.auth import get_user_model

random.seed()


class TestPaymentModel(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create(username='test_user')
        cls.user.save()

    def create_payment(self):
        params = {
            "Amount": "100",
            "OrderId": str(random.randint(5, 100000)),
            "Description": "test payment",
            "Receipt": {
                "Email": "a@test.ru",
                "Phone": "+79031234567",
                "EmailCompany": "b@test.ru",
                "Taxation": "osn",
                "Items": [
                    {
                        "Name": "name 1",
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
        payment = PaymentModel.create_payment(params)
        payment.save()
        self.assertEqual(payment.status, 'NEW')
        return payment

    def get_state(self):
        payment = self.create_payment()
        payment.get_state()
        self.assertEqual(payment.status, 'NEW')
        input(f'enter card data to form: {payment.payment_url}, then press any key')
        payment.get_state()
        self.assertEqual(payment.status, 'CONFIRMED')
        return payment

    def test_payment_cycle(self):
        payment = self.create_payment()
        payment.cancel()
        self.assertEqual(payment.status, 'CANCELED')
        payment = self.get_state()
        payment.cancel()
        self.assertEqual(payment.status, 'REFUNDED')
