import re

from aiogram import types, Bot
from asgiref.sync import sync_to_async, async_to_sync
from django.conf import settings
from django.db import models
from loguru import logger
from rr_backend.backend import Backend
from asyncio.exceptions import TimeoutError
from rr_backend.rosreestr import TemporaryUnavalible

from cabinet.models import User, Service, Curency, Bill, Order
from .tasks import update_bill_status
bot = Bot(token=settings.TELEGRAM_API_TOKEN)


@async_to_sync
async def send_message(*args, **kwargs):
    return await bot.send_message(*args, parse_mode='HTML', **kwargs)


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


def conditions_accepted_permission(method):
    def wraper(*args, **kwargs):
        user = args[0].user
        if user.conditions_accepted:
            return method(*args, **kwargs)
        else:
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='Скачать документы', callback_data='download_conditions')
            keyboard.add(button)
            return 'Чтобы продолжить необходимо принять условия пользования сервисом', keyboard
    return wraper


class BalanceDialog(models.Model):
    class Meta:
        verbose_name = 'Диалог'

    user = models.OneToOneField(User, to_field='telegram_id',
                                on_delete=models.CASCADE,
                                verbose_name='Пользователь',
                                db_index=True,
                                primary_key=True)
    data = models.JSONField(default=dict, max_length=8096)
    resolver = models.TextField(max_length=32, null=True)

    chat_id = None

    def send_message(self, text, reply_markup=None):
        send_message(chat_id=self.chat_id, text=text, reply_markup=reply_markup)

    def flush(self):
        # main_dialog, _ = Dialog.objects.get_or_create(pk=self.user)
        # main_dialog.flush()
        logger.debug('dialog flushed')
        self.data = {}
        self.resolver = None
        self.save()

    def set_resolver(self, resolver_name: str):
        self.resolver = resolver_name
        self.save()

    @classmethod
    def callback_resolv(cls, callback: types.CallbackQuery):
        user_id = callback.from_user.id
        obj, _ = cls.objects.get_or_create(pk=user_id)
        obj.chat_id = callback.message.chat.id
        data = callback.data
        logger.debug(data)

        # refill dialog entry point
        if data == 'refill':
            # obj.flush()
            return obj.press_refill(data)
        # change email entry point
        if data == 'change_email':
            obj.flush()
            return obj.press_change_email(data)
        if data == 'orders':
            obj.flush()
            return obj.press_orders(data)
        if data == 'download_conditions':
            # obj.flush()
            return obj.press_download_conditions(data)
        if data == 'accept_conditions':
            # obj.flush()
            return obj.press_accept_conditions(data)

        resolver = obj.get_resolver()
        return resolver(data)

    @classmethod
    def message_resolv(cls, message: types.Message):
        user_id = message.from_user.id
        text = message.text
        logger.debug(text)
        obj, _ = cls.objects.get_or_create(pk=user_id)
        obj.chat_id = message.chat.id

        # help message entry point
        if text == 'Помощь':
            return obj.input_help(text)
        # purse entry point
        if text == 'Кошелек':
            obj.flush()
            return obj.press_purse(text)
        # my account entry point
        if text == 'Аккаунт':
            obj.flush()
            return obj.press_my_account(text)
        if text == 'Заказы':
            obj.flush()
            return obj.press_orders(text)
        if re.match(r'.* .* .*', text):
            obj.flush()
            return obj.input_adress_string(text)

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
        return f'Упс...\nВы тыкнули када то не туда)\nИли сказали что-то непонятное)\nНачните диалог заново.', None

    def press_download_conditions(self, data):
        keyboard = types.InlineKeyboardMarkup()
        join_button = types.InlineKeyboardButton(text='Принять', callback_data='accept_conditions')
        keyboard.add(join_button)
        file1 = types.InputFile(settings.ROSREESTR_POLICY_FILE, filename='политика.doc')
        file2 = types.InputFile(settings.ROSREESTR_OFFERTA_FILE, filename='оферта.doc')
        self.set_resolver('press_accept_conditions')
        return [(None, file1), (None, file2), ('Если вы согласны с условиями, нажмите кнопку', keyboard)]

    def press_accept_conditions(self, data):
        if data == 'accept_conditions':
            self.user.conditions_accepted = True
            self.user.save()
            self.flush()
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            help_button = types.KeyboardButton('Помощь')
            orders_button = types.KeyboardButton('Заказы')
            account_button = types.KeyboardButton('Аккаунт')
            purse_button = types.KeyboardButton('Кошелек')
            keyboard.add(help_button, account_button)
            keyboard.add(orders_button, purse_button)
            return [('Теперь можете продолжить работу с сервисом', keyboard), self.input_help('')]
        else:
            return self.default_resolver(data)

    def press_refill(self, data: str, message=None):
        # self.flush()
        bill_set = Bill.objects.filter(user=self.user, is_payed=False)

        for bill in bill_set:
            bill.update_payment()

        filtred_bill_set = bill_set.filter(is_payed=False)

        if len(filtred_bill_set) > 0:
            bill = filtred_bill_set.first()
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='Отменить этот платеж', callback_data=f'cancel: {bill.id}')
            url = types.InlineKeyboardButton(text='Оплатить через Tinkoff', url=bill.payment.payment_url)
            keyboard.add(url)
            keyboard.add(button)
            self.set_resolver('press_cancel_payment')
            return f'У вас уже есть неплаченный счет:\n {bill.amount / 100} RUR', keyboard

        if self.user.email == '':
            self.set_resolver('input_email')
            self.data = {'return_to': 'input_amount', 'return_message': 'Выбирете сумму, либо введите вручную:'}
            self.save()
            return f'Нобходимо <b>указать email</b> для получения чеков:', None

        self.set_resolver('input_amount')
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text=f'100 {settings.DEFAULT_CURENCY}', callback_data=100)
        button2 = types.InlineKeyboardButton(text=f'250 {settings.DEFAULT_CURENCY}', callback_data=250)
        button3 = types.InlineKeyboardButton(text=f'500 {settings.DEFAULT_CURENCY}', callback_data=500)
        button4 = types.InlineKeyboardButton(text=f'1000 {settings.DEFAULT_CURENCY}', callback_data=1000)
        keyboard.row(button1, button2)
        keyboard.row(button3, button4)
        return 'Выбирете сумму, либо введите вручную:', keyboard

    def press_cancel_payment(self, data: str):
        bill_id = int(data.split(' ')[1])
        bill = Bill.objects.get(pk=bill_id)
        bill.payment.cancel()
        bill.delete()
        self.flush()
        return f'Платеж отменен!', None

    def input_amount(self, text: str):
        if not text.isnumeric():
            return 'Вводить нужно число!', None
        self.data['amount'] = text
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
            update_bill_status.delay(bill.id, self.user.telegram_id)
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='Оплатить через Tinkoff', url=bill.payment.payment_url)
            keyboard.add(button)
            if self.data['return_to']:
                if self.data['return_to'] == 'press_on_service':
                    self.set_resolver('press_on_service')
                    keyboard2 = types.InlineKeyboardMarkup()
                    button2 = types.InlineKeyboardButton(text='Прдолжить оформление',
                                                         callback_data=self.data['return_data'])
                    keyboard2.add(button2)
                    return [('Сформирован счетна оплату', keyboard),
                            ('После совершения оплаты, можете продолжить оформление заказа', keyboard2)]
            return f'Сформирован счетна оплату', keyboard

    def input_help(self, text: str):
        # self.flush()
        return '''Для поиска введите <b>адрес</b> или <b>кадастровый номер</b> объекта недвижимости''', None

    @conditions_accepted_permission
    def press_purse(self, tet: str):
        # self.flush()
        purse, _ = self.user.purse_set.get_or_create(curency__name=settings.DEFAULT_CURENCY)
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text='Пополнить', callback_data='refill')
        keyboard.add(button)
        return f'Баланс: {purse.ammount} {settings.DEFAULT_CURENCY}', keyboard

    def press_my_account(self, text: str):
        # self.flush()
        keyboard = types.InlineKeyboardMarkup()
        top_up_balance = types.InlineKeyboardButton(text='Поплнить баланс', callback_data='refill')
        orders = types.InlineKeyboardButton(text='Заказы', callback_data='orders')
        referal = types.InlineKeyboardButton(text='Рефералка', callback_data='referal')
        change_email = types.InlineKeyboardButton(text='Изменить email', callback_data='change_email')
        keyboard.add(top_up_balance)
        keyboard.add(orders)
        keyboard.add(referal)
        keyboard.add(change_email)
        text = f'''<b>Ваш ID</b>: {self.user.telegram_id}
<b>Email</b>: {self.user.email}
<b>Баланс</b>: {self.user.purse_set.get(curency__name=settings.DEFAULT_CURENCY).ammount}
'''
        # Вы с нами с: {self.user.date_joined.strftime('%d.%m.%Y')}

        return text, keyboard

    @conditions_accepted_permission
    def press_change_email(self, data):
        # self.flush()
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
            if self.data['return_to']:
                self.set_resolver(self.data['return_to'])
                keyboard = types.InlineKeyboardMarkup()
                button1 = types.InlineKeyboardButton(text=f'100 {settings.DEFAULT_CURENCY}', callback_data=100)
                button2 = types.InlineKeyboardButton(text=f'250 {settings.DEFAULT_CURENCY}', callback_data=250)
                button3 = types.InlineKeyboardButton(text=f'500 {settings.DEFAULT_CURENCY}', callback_data=500)
                button4 = types.InlineKeyboardButton(text=f'1000 {settings.DEFAULT_CURENCY}', callback_data=1000)
                keyboard.row(button1, button2)
                keyboard.row(button3, button4)
                return f'email изменен на: {self.user.email} \n{self.data["return_message"]}', keyboard
            else:
                self.flush()
            return f'email изменен на: {self.user.email}', None
        else:
            return 'Это не похоже на правильный email', None

    @conditions_accepted_permission
    def press_orders(self, data: str):
        # self.flush()
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

    def input_adress_string(self, data: str):
        self.flush()
        addr_variants = Backend.find_adress(data, self.chat_id)
        if len(addr_variants) == 0:
            return 'Такой адресс не найден, уточните адрес и повторите попытку', None
        else:
            self.data = {'addr_variants': addr_variants[0]}
            self.set_resolver('press_next_on_adsress')
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='Далее', callback_data='next')
            keyboard.row(button)
            return self.data['addr_variants']['value'], keyboard

    def press_next_on_adsress(self, data: str):
        if data != 'next':
            return self.default_resolver(data)
        try:
            results = Backend.objects_by_address(self.data['addr_variants'], self.chat_id)
        except (TimeoutError, TemporaryUnavalible):
            return 'Cервисы Росреестра в настоящий момент недоступны, попробуйте позже', None
        except:
            logger.exception(f'Error on search address: {self.data["addr_variants"]["value"]}')
            return 'Низвестная ошибка!!! Мы уже разбираемся с этим', None

        if len(results) == 0:
            return 'К сожалению не удалось найти информацию об объекте', None

        self.data['search_results'] = results
        self.set_resolver('press_on_object_variant')
        text = str()
        buttons = []
        for i, result in enumerate(results):
            if result['error']:
                continue
            text += f'\n<b>Объект {i + 1}:</b>'
            buttons.append(types.InlineKeyboardButton(text=f'Объект {i + 1}', callback_data=f'object_{i}'))
            text += f"\n{result['EGRN']['object']['CADNOMER']} - {result['EGRN']['object']['ADDRESS']}"
            text += f"\nСтатус объекта: {result['EGRN']['details']['Статус объекта']}\n" or 'Неизвестно\n'

        keyboard = types.InlineKeyboardMarkup()
        for button in buttons:
            keyboard.add(button)
        return text, keyboard

    def press_on_object_variant(self, data: str):

        if 'object' not in data:
            return self.default_resolver(data)

        object_id = int(data.split('_')[1])

        variant = self.data['search_results'][object_id]
        self.data['choosen_variant'] = variant
        self.set_resolver('press_on_service')
        logger.debug(self.data["choosen_variant"]["EGRN"]["object"]["ADDRESS"])
        text = f'<b>Информация по объекту</b>\n'
        logger.debug(variant)
        output = {
            'Кадастровый номер': variant['EGRN']['details']['Кадастровый номер'] or '',
            'Адрес': variant["EGRN"]["object"]["ADDRESS"] or '',
            'Объект': f"{variant['EGRN']['details']['(ОКС) Тип']} ({variant['EGRN']['details']['(ОКС) Этажность']} эт.)" or '',
            # 'Год ввода': variant['EGRN']['details']['Кадастровый номер'] or ''
            'Кадастровая стоимость': f"{variant['EGRN']['details']['Кадастровая стоимость']} ({variant['EGRN']['details']['Дата внесения стоимости']} г.)",
            'Площадь': variant['EGRN']['details']['Площадь ОКС\'а'],
            'Количество правообладателей': variant['EGRN']['details']['Количество правообладателей'],
            'Вид собственности': f"{variant['EGRN']['rights'][0]['type']} (от {variant['EGRN']['rights'][0]['date']} г.)",
            'Обременения': 'Зафиксированы' if len(variant['EGRN']['rights'][0]) > 0 else 'Не зафиксированы'
        }
        logger.debug(output)
        for key, value in output.items():
            text += f'\n<b>{key}</b>: {value}'

        price_list = Service.price_list()
        keyboard = types.InlineKeyboardMarkup()
        for price in price_list:
            button = types.InlineKeyboardButton(text=f'{price["short_name"]} за {price["price"]}',
                                                callback_data=f'service_{price["id"]}')
            keyboard.add(button)
        return text, keyboard

    def press_on_service(self, data: str):
        if 'service' not in data:
            return self.default_resolver(data)

        service_id = int(data.split('_')[1])

        self.data['service_id'] = service_id
        self.save()
        curency = Curency.objects.get(name__exact=settings.DEFAULT_CURENCY)
        service = Service.objects.get(pk=service_id)
        money_is_enough = service.check_ammount(self.user, curency)
        purse = self.user.purse_set.get(curency=curency)
        if money_is_enough:
            self.set_resolver('press_confirm_order')
            keyboard = types.InlineKeyboardMarkup()
            button_ok = types.InlineKeyboardButton(text='Да, все верно, офрмить заказ', callback_data='confirm')
            button_cancel = types.InlineKeyboardButton(text='Отменить', callback_data='cancel')
            keyboard.add(button_ok)
            keyboard.add(button_cancel)
            return f'''Подтвердите ваш заказ:
Адресс: {self.data["choosen_variant"]["EGRN"]["object"]["ADDRESS"]}
Кадастровый номер: {self.data["choosen_variant"]["EGRN"]["object"]["CADNOMER"]}
Услуга: {service.name}
Стоимость: {service.get_price()}
На счете останется: {purse.ammount - service.get_price()}''', keyboard
        else:
            self.data['return_to'] = 'press_on_service'
            self.data['return_data'] = data
            self.save()
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='Пополнить счет', callback_data='refill')
            keyboard.add(button)
            return f'У вас на счете: {purse.ammount}, небходимо {service.get_price()}. ' \
                   f'Для продолжения <b>пополните счет</b>', keyboard
