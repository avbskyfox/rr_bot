from loguru import logger
from aiogram import types
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import models
import re

from cabinet.models import User, Service, Curency, Bill, Order
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

    def set_resolver(self, resolver_name: str):
        self.resolver = resolver_name
        self.save()

    @classmethod
    def callback_resolv(cls, callback: types.CallbackQuery):
        user_id = callback.from_user.id
        obj, _ = cls.objects.get_or_create(pk=user_id)
        data = callback.data
        logger.debug(data)

        # refill dialog entry point
        if data == 'refill':
            return obj.press_refill(data)
        # change email entry point
        if data == 'change_email':
            return obj.press_change_email(data)
        if data == 'orders':
            return obj.press_orders(data)

        resolver = obj.get_resolver()
        return resolver(data)

    @classmethod
    def message_resolv(cls, message: types.Message):
        user_id = message.from_user.id
        text = message.text
        logger.debug(text)
        obj, _ = cls.objects.get_or_create(pk=user_id)

        # help message entry point
        if text == 'Help':
            return obj.input_help(text)
        # purse entry point
        if text == 'Purse':
            return obj.press_purse(text)
        # my account entry point
        if text == 'My account':
            return obj.press_my_account(text)

        resolver = obj.get_resolver()
        return resolver(text)

    @classmethod
    @sync_to_async
    def async_callback_resolv(cls, callback: types.CallbackQuery):
        return cls.callback_resolv(callback)

    @classmethod
    @sync_to_async
    def async_message_resolv(cls, message: types.CallbackQuery):
        return cls.message_resolv(message)

    def get_resolver(self):
        return getattr(self, str(self.resolver), self.default_resolver)

    def default_resolver(self, data):
        return 'Упс...\nВы тыкнули када то не туда)\nИли сказали что-то непонятное)\nНачните диалог заново.', None

    def press_refill(self, data: str):
        self.flush()
        bill_set = Bill.objects.filter(user=self.user, is_payed=False)
        for bill in bill_set:
            bill.update_payment()
        filtred_bill_set = bill_set.filter(is_payed=False)
        if len(filtred_bill_set) > 0:
            bill = filtred_bill_set.first()
            return f'У вас уже есть неплаченный счет: {bill.amount / 100} RUR: {bill.payment.payment_url}', None
        self.resolver = 'input_amount'
        self.save()
        return 'Введите количество:', None

    def input_amount(self, text: str):
        if not text.isnumeric():
            return 'Вводить нужно число!', None
        self.data = {'amount': text}
        self.resolver = 'press_amount_yes_no'
        self.save()
        keyboard = types.InlineKeyboardMarkup()
        yes_button = types.InlineKeyboardButton(text='yes', callback_data='y')
        no_button = types.InlineKeyboardButton(text='no', callback_data='n')
        keyboard.add(yes_button, no_button)
        return f'Пополнить счет на {text} RUR?', keyboard

    def press_amount_yes_no(self, data: str):
        if data == 'n':
            self.flush()
            return None, None
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

    def input_help(self, text: str):
        self.flush()
        return 'Help message', None

    def press_purse(self, tet: str):
        self.flush()
        purse = self.user.purse_set.get(curency__name=settings.DEFAULT_CURENCY)
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text='Пополнить', callback_data='refill')
        keyboard.add(button)
        return f'Баланс: {purse.ammount} {settings.DEFAULT_CURENCY}', keyboard

    def press_my_account(self, text: str):
        self.flush()
        keyboard = types.InlineKeyboardMarkup()
        top_up_balance = types.InlineKeyboardButton(text='Поплнить баланс', callback_data='refill')
        orders = types.InlineKeyboardButton(text='Заказы', callback_data='orders')
        referal = types.InlineKeyboardButton(text='Рефералка', callback_data='referal')
        change_email = types.InlineKeyboardButton(text='Изменить email', callback_data='change_email')
        keyboard.add(top_up_balance)
        keyboard.add(orders)
        keyboard.add(referal)
        keyboard.add(change_email)
        text = f'''Ваш ID: {self.user.telegram_id}
<b>Email</b> : {self.user.email}
Вы с нами с: {self.user.date_joined.strftime('%d.%m.%Y')}
Баланс: {self.user.purse_set.get(curency__name=settings.DEFAULT_CURENCY).ammount}
'''
        return text, keyboard

    def press_change_email(self, data):
        self.flush()
        self.set_resolver('input_email')
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text='Отменить', callback_data='cancel_email')
        keyboard.add(button)
        return 'Хотите изменить email? Тогда введите новый:', keyboard

    def input_email(self, text: str):
        if text == 'cancel_email':
            self.flush()
            return f'Ну ладно, оставим этот: {self.user.email}', None
        regexp = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE)
        if regexp.match(text):
            self.user.email = text.lower()
            self.user.save()
            self.flush()
            return f'email изменен на: {self.user.email}', None
        else:
            return 'Это не похоже на правильный email', None

    def press_orders(self, data: str):
        self.flush()
        self.set_resolver('press_new_old')
        keyboard = types.InlineKeyboardMarkup()
        new_button = types.InlineKeyboardButton(text='Новые', callback_data='new_orders')
        old_button = types.InlineKeyboardButton(text='Исполненные', callback_data='old_orders')
        keyboard.add(new_button)
        keyboard.add(old_button)
        return 'Выбирете:', keyboard

    def press_new_old(self, data: str):
        orders = []
        if data == 'new_orders':
            orders = [order for order in self.user.order_set.all() if not order.is_finished]
        elif data == 'old_orders':
            orders = [order for order in self.user.order_set.all() if order.is_finished]
        result = []
        for order in orders:
            text = f'{order.number} от {order.date_created.strftime("%d.%m.%Y")}'
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='Прсмотреть', callback_data=f'order: {order.id}')
            keyboard.add(button)
            result.append((text, keyboard))
        self.set_resolver('press_view_order')
        return result

    def press_view_order(self, data: str):
        if data.find('order: ') == 0:
            order_id = int(data.split(' ')[1])
            order = self.user.order_set.get(pk=order_id)
            text = f'Заказ № {order.number} от {order.date_created.strftime("%d.%m.%Y")}\n для адреса {order.address}\n'
            for exerpt in order.excerpt_set.all():
                text += f'{exerpt.type.name}\n'
            return text, None
        return None, None
