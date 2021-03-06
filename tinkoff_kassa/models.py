import requests
from django.conf import settings
from django.db import models

from tinkoff_kassa.exceptions import *
from tinkoff_kassa.misc import generate_token
from tinkoff_kassa.tinkoff_urls import *


class PaymentModel(models.Model):
    terminal_key = models.TextField(verbose_name='Идентификатор терминала', max_length=20)
    amount = models.IntegerField(verbose_name='Сумма (коп.)')
    order_id = models.TextField(verbose_name='Идентификатор заказа у прдавца', max_length=36)
    status = models.TextField(verbose_name='Статус платежа', max_length=20)
    payment_id = models.IntegerField(verbose_name='Идентификатор платежа в системе банка')
    payment_url = models.URLField(verbose_name='Ссылка на платежную форму', blank=True)
    is_confirmed = models.BooleanField(default=False)
    is_canceled = models.BooleanField(default=False)
    params = models.JSONField(verbose_name='Параметры платежа')

    def __str__(self):
        return self.order_id

    @staticmethod
    def create_payment(params: dict):
        params['TerminalKey'] = settings.TINKOFF_TERMINAL
        params['Token'] = generate_token(params)
        response = requests.post(init_url, json=params)
        if response.status_code != 200:
            raise HttpError({'params': params, 'status_code': response.status_code})
        data = response.json()
        if not data['Success']:
            raise PaymentCreationError({'params': params, 'data': data})
        payment = PaymentModel(
            terminal_key=data.get('TerminalKey', ''),
            amount=data.get('Amount', 0),
            order_id=data.get('OrderId', ''),
            status=data.get('Status', ''),
            payment_id=data.get('PaymentId', 0),
            payment_url=data.get('PaymentURL', ''),
            params=params
        )
        payment.save()
        return payment

    def finish_authorise(self):
        pass

    def confirm(self):
        pass

    def cancel(self):
        params = {'TerminalKey': settings.TINKOFF_TERMINAL, 'PaymentId': str(self.payment_id)}
        params['Token'] = generate_token(params)
        response = requests.post(cancel_url, json=params)
        if response.status_code != 200:
            raise HttpError({'params': params, 'status_code': response.status_code})
        data = response.json()
        if not data['Success']:
            raise PaymentCancelError({'params': params, 'data': data})
        self.status = data['Status']
        self.amount = data['NewAmount']
        self.is_canceled = True
        self.save()

    def get_state(self):
        params = {'TerminalKey': settings.TINKOFF_TERMINAL, 'PaymentId': str(self.payment_id)}
        params['Token'] = generate_token(params)
        response = requests.post(get_state_url, json=params)
        if response.status_code != 200:
            raise HttpError({'params': params, 'status_code': response.status_code})
        data = response.json()
        if not data['Success']:
            raise GetStateError({'params': params, 'data': data})
        self.status = data['Status']
        self.success = data['Success']
        self.error_code = data['ErrorCode']
        self.message = data['Message']
        if self.status == 'CONFIRMED':
            self.is_confirmed = True
        if self.status == 'CANCELED':
            self.is_canceled = True
        if self.status == 'REJECTED':
            self.is_canceled = True
        if self.status == 'DEADLINE_EXPIRED':
            self.is_canceled = True
        self.save()

    def resend(self):
        pass

    def submith_3d_authorization(self):
        pass
