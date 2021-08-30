import loguru
from aiogram import types
from asgiref.sync import sync_to_async
from django.db import models
from django.conf import settings

from cabinet.models import User, Service, Curency, Bill
from tinkoff_kassa.models import PaymentModel


class Dialog(models.Model):
    class Meta:
        verbose_name = 'Диалог'

    telegram_id = models.OneToOneField(User, to_field='telegram_id',
                                       on_delete=models.CASCADE,
                                       verbose_name='Пользователь',
                                       db_index=True,
                                       primary_key=True)
    step = models.IntegerField(verbose_name='Шаг', default=0)
    data = models.JSONField(verbose_name='Данные', default=dict)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name='Услуга', null=True)
    curency = models.ForeignKey(Curency, on_delete=models.CASCADE, verbose_name='Валюта', null=True)
    number = models.CharField(max_length=30, verbose_name='Кадастровый номер', blank=True)
    address = models.CharField(max_length=255, verbose_name='Строка адреса', blank=True)
    dadata = models.JSONField(max_length=4096, verbose_name='Данные дадата', null=True)

    def serialize(self):
        purse = self.telegram_id.purse_set.get(curency=self.curency)
        return {
            'step': self.step,
            'service': self.service.serialize(),
            'curency': self.curency,
            'number': self.number,
            'address': self.address,
            'purse_ammount': purse.ammount,
            'check_ammount': self.service.check_ammount(self.telegram_id, self.curency)
        }

    def flush(self):
        self.step = 0
        self.data = {}
        self.save()


class BalanceDialog(models.Model):
    class Meta:
        verbose_name = 'Диалог'

    user = models.OneToOneField(User, to_field='telegram_id',
                                on_delete=models.CASCADE,
                                verbose_name='Пользователь',
                                db_index=True,
                                primary_key=True)
    data = models.JSONField(null=True)
    resolver = models.TextField(max_length=32, null=True)

    def flush(self):
        self.data = None
        self.resolver = None
        self.save()

    @classmethod
    def resolv(cls, telegram_data):
        if isinstance(telegram_data, types.CallbackQuery):
            user_id = telegram_data.from_user.id
            obj, _ = cls.objects.get_or_create(pk=user_id)
            data = telegram_data.data
            if data == 'refill':
                return obj.press_refill(data)
            resolver = obj.get_resolver()
            return resolver(data)

        if isinstance(telegram_data, types.Message):
            user_id = telegram_data.from_user.id
            text = telegram_data.text
            obj, _ = cls.objects.get_or_create(pk=user_id)
            resolver = obj.get_resolver()
            return resolver(text)

    @classmethod
    @sync_to_async
    def async_resolv(cls, telegram_data):
        return cls.resolv(telegram_data)

    def get_resolver(self):
        return getattr(self, str(self.resolver), self.press_refill)

    def press_refill(self, data: str):
        bill_set = Bill.objects.filter(user=self.user, is_payed=False)
        for bill in bill_set:
            bill.update_payment()
        filtred_bill_set = bill_set.filter(is_payed=False)
        loguru.logger.debug(filtred_bill_set)
        if len(filtred_bill_set) > 0:
            bill = filtred_bill_set.first()
            return f'U already have unpayed bill for {bill.amount/100}: {bill.payment.payment_url}', []
        self.resolver = 'input_amount'
        self.save()
        return 'Enter amount:', []

    def input_amount(self, text: str):
        if not text.isnumeric():
            return 'Enter amount:', []
        self.data = {'amount': text}
        self.resolver = 'press_amount_yes_no'
        self.save()
        return f'Refill {text} RUR', [{'text': 'YES', 'callback': 'y'}, {'text': 'NO', 'callback': 'n'}]

    def press_amount_yes_no(self, data: str):
        if data == 'n':
            self.flush()
        elif data == 'y':
            self.data['yes_no'] = data
            amount = int(self.data['amount']) * 100
            curency = Curency.objects.get(name=settings.DEFAULT_CURENCY)
            bill = Bill.objects.create(user=self.user,
                                       curency=curency,
                                       amount=amount,
                                       price=amount * curency.course)
            bill.create_payment()
            return f'{bill.payment.payment_url}', []
