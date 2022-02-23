from django.test import TestCase
from cabinet.models import Bill, User, Purse, Curency
from loguru import logger
from django.conf import settings


settings.TINKOFF_TERMINAL = '1634909634238DEMO'
settings.TINKOFF_PASSWORD = '62lyvz8whpiflu3u'


class TestBill(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='test_user', email='test_user@email.ts', phone_number='79995598230')
        cls.curency = Curency.objects.create(name='RUR')
        Purse.objects.create(user=cls.user, curency=cls.curency)
        super().setUpTestData()

    def test_success_payment(self):
        bill = Bill.objects.create(user=self.user, amount=100, price=100, curency=self.curency)
        bill.create_payment()
        logger.success(bill.payment.payment_url)
        inp = input(f'Оплатите картой 4300 0000 0000 0777 и нажмите клавишу:')
        bill.update_payment()
        if not bill.is_payed:
            self.fail('платеж не оплачен')

    def test_insificient_funds(self):
        bill = Bill.objects.create(user=self.user, amount=100, price=100, curency=self.curency)
        bill.create_payment()
        logger.success(bill.payment.payment_url)
        inp = input(f'Оплатите картой 5000 0000 0000 0009 и нажмите клавишу:')
        bill.update_payment()
        logger.debug(bill.payment.status)
        self.assertEqual('REJECTED', bill.payment.status)
        if bill.is_payed:
            self.fail('платеж оплачен')

    def test_cancel_success_payment(self):
        bill = Bill.objects.create(user=self.user, amount=100, price=100, curency=self.curency)
        bill.create_payment()
        logger.success(bill.payment.payment_url)
        inp = input(f'Оплатите картой 4000 0000 0000 0119 и нажмите клавишу:')
        bill.update_payment()
        self.assertTrue(bill.is_payed)
        bill.cancel_payment()
        logger.debug(bill.payment.status)
        self.assertEqual('REFUNDED', bill.payment.status)

    def test_success_payment_with_check(self):
        bill = Bill.objects.create(user=self.user, amount=100, price=100, curency=self.curency)
        bill.create_payment()
        logger.success(bill.payment.payment_url)
        inp = input(f'Оплатите картой 4000 0000 0000 0101 и нажмите клавишу:')
        bill.update_payment()
        if not bill.is_payed:
            self.fail('платеж не оплачен')

    def test_cancel_success_payment_with_check(self):
        bill = Bill.objects.create(user=self.user, amount=100, price=100, curency=self.curency)
        bill.create_payment()
        logger.success(bill.payment.payment_url)
        inp = input(f'Оплатите картой 5000 0000 0000 0108 и нажмите клавишу:')
        bill.update_payment()
        self.assertTrue(bill.is_payed)
        bill.cancel_payment()
        logger.debug(bill.payment.status)
        self.assertEqual('REFUNDED', bill.payment.status)