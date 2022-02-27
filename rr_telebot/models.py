import re
from asyncio.exceptions import TimeoutError

from aiogram import types
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import models
from django.utils import timezone
from loguru import logger

from cabinet.models import User, Service, Curency, Bill, Order, OrderException, BackendException, Excerpt
from rr_backend.backend import Backend
from rr_backend.rosreestr import TemporaryUnavalible, NotFound
from .tasks import update_bill_status, send_to_adm_group, notify_user


def conditions_accepted_permission(method):
    def wraper(*args, **kwargs):
        def is_done_char(expression: bool):
            return '✅' if expression else '❌'

        user = args[0].user
        is_condition = user.conditions_accepted
        is_email = True if user.email != '' else False
        is_phone = True if user.phone_number != '' else False
        if not is_email:
            t_button = 'Указать email'
        elif not is_phone:
            t_button = 'Указать номер телефона'
        elif not is_condition:
            t_button = '👉Правила работы сервиса'
        try:
            assert is_condition
            assert is_email
            assert is_phone
        except AssertionError:
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text=t_button, callback_data='authorization')
            keyboard.add(button)
            text = f'''Для того, что бы пользоваться сервисом необходимо авторизоваться. Для этого пройдите три простых шага:
{is_done_char(is_email)} Введите адресс электронной почты
{is_done_char(is_phone)} Введите номер телефона
{is_done_char(is_condition)} Примите условия использования сервиса
            '''
            return text, keyboard
        else:
            return method(*args, **kwargs)

    return wraper


class Ticket(models.Model):
    class Meta:
        verbose_name = 'Тикет'
        verbose_name_plural = 'Тикеты'

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Пользователь')
    description = models.TextField(max_length=8192, blank=True, verbose_name='Описание')
    solution = models.TextField(max_length=8192, blank=True, verbose_name='Решение')
    closed = models.BooleanField(default=False, verbose_name='Закрыт?')
    user_notify_message = models.TextField(max_length=8192, blank=True, verbose_name='Сообщение пользователю')
    need_notify_user = models.BooleanField(default=False, verbose_name='Уведомить пользователя?')

    def notify(self):
        notify_user.delay(self.user.telegram_id, self.user_notify_message)

    def save(self, *args, **kwargs):
        if self.closed:
            send_to_adm_group(f'Тикет {self.id} закрыт: {self.description}')
        if self.need_notify_user:
            self.notify()
        super(Ticket, self).save(*args, **kwargs)
        if not self.closed:
            send_to_adm_group(f'Тикет {self.id} создан: {self.description}')

    def __str__(self):
        return str(self.id)


class Review(models.Model):
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Пользователь')
    text = models.TextField(max_length=8192, blank=True, verbose_name='Описание')
    grade = models.IntegerField(null=True)

    def __str__(self):
        return f'{str(self.id)} - {self.user.username}'


class SearchHistory(models.Model):
    class Meta:
        verbose_name = 'История поисков'

    user = models.OneToOneField(User, to_field='telegram_id',
                                on_delete=models.CASCADE,
                                verbose_name='Пользователь',
                                db_index=True,
                                primary_key=True)
    data = models.JSONField(default=list, max_length=8192, verbose_name='Данные')
    last_search_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(f'{self.user.username}')

    def save_to_history(self, dadata):
        self.delete_yestoday()
        self.last_search_date = timezone.now()
        self.data.insert(0, dadata)
        if len(self.data) > 5:
            self.data.pop()
        self.save()

    def delete_yestoday(self):
        now = timezone.now().today()
        if self.last_search_date.day == now.day and self.last_search_date.month == now.month:
            pass
        else:
            self.data = []
            self.save()


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

    def __str__(self):
        return f'{self.user.username}_dialog'

    chat_id = None

    def flush(self):
        # main_dialog, _ = Dialog.objects.get_or_create(pk=self.user)
        # main_dialog.flush()
        logger.debug(f'dialog {str(self)} flushed')
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
        # refill dialog entry point
        if data == 'join':
            return obj.press_join(data)
        if data == 'refill':
            # obj.flush()
            return obj.press_refill(data)
        # change email entry point
        if data == 'change_email':
            obj.flush()
            return obj.press_change_email(data)
        if data == 'change_phone':
            obj.flush()
            return obj.press_change_phone(data)
        if data == 'orders':
            obj.flush()
            return obj.press_orders(data)
        if data == 'authorization':
            # obj.flush()
            return obj.press_authorization(data)
        if data == 'accept_conditions':
            # obj.flush()
            return obj.press_accept_conditions(data)
        if data == 'feedback':
            return obj.press_feedback(data)

        resolver = obj.get_resolver()
        return resolver(data)

    @classmethod
    def message_resolv(cls, message: types.Message):
        user_id = message.from_user.id
        text = message.text
        obj, _ = cls.objects.get_or_create(pk=user_id)
        obj.chat_id = message.chat.id

        # help message entry point
        if text == '🛎 Помощь':
            return obj.input_help(text)
        # purse entry point
        if text == '💰 Кошелек':
            obj.flush()
            return obj.press_purse(text)
        # my account entry point
        if text == '⭐ Аккаунт':
            obj.flush()
            return obj.press_my_account(text)
        if text == '📝 Заказы':
            obj.flush()
            return obj.press_orders(text)
        if text == '📝 История':
            obj.flush()
            return obj.press_history(text)

        resolver = obj.get_resolver()

        if re.match(r'.* .* .*', text):
            obj.flush()
            return obj.input_adress_string(text)

        if re.match(r"^(\d\d):(\d\d):*", text):
            obj.flush()
            return obj.input_cadastr_number(text)

        return resolver(text)

    @classmethod
    def contact_resolv(cls, message: types.Message):
        user_id = message.from_user.id
        obj, _ = cls.objects.get_or_create(pk=user_id)
        obj.chat_id = message.chat.id
        return obj.input_phone(message)

    @classmethod
    @sync_to_async(thread_sensitive=False)
    def async_callback_resolv(cls, callback: types.CallbackQuery):
        return cls.callback_resolv(callback)

    @classmethod
    @sync_to_async(thread_sensitive=False)
    def async_message_resolv(cls, message: types.Message):
        return cls.message_resolv(message)

    @classmethod
    @sync_to_async(thread_sensitive=False)
    def async_contact_resolv(cls, message: types.CallbackQuery):
        return cls.contact_resolv(message)

    def get_resolver(self):
        return getattr(self, str(self.resolver), self.default_resolver)

    def default_resolver(self, data):
        return f'Упс...\nВы нажали куда-то не туда :)\nИли сказали что-то непонятное :)\n' \
               f'Пожалуйста, начните диалог заново.', None

    def press_join(self, data):
        if data == 'join':
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            help_button = types.KeyboardButton('🛎 Помощь')
            orders_button = types.KeyboardButton('📝 История')
            account_button = types.KeyboardButton('⭐ Аккаунт')
            purse_button = types.KeyboardButton('💰 Кошелек')
            keyboard.add(help_button, account_button)
            keyboard.add(orders_button, purse_button)
            # keyboard.add(purse_button)
            text = '''Привет! 
Это бот-помощник «Террагент»
Территория для агентов по недвижимости.

Здесь Вы можете:
✔ Узнать информацию об объекте недвижимости: (<b>Выписка-отчет</b>)

'''
            return [(text, keyboard), self.input_help('')]

    def press_authorization(self, data):
        if data != 'authorization':
            return self.default_resolver(data)
        is_condition = self.user.conditions_accepted
        is_email = True if self.user.email != '' else False
        is_phone = True if self.user.phone_number != '' else False
        if not is_email:
            self.data['return_to_authorization'] = True
            self.data['return_data'] = data
            self.set_resolver('input_email')
            return 'Для начала укажите Ваш email. На него мы будем отправлять чеки и документы:', None
        if not is_phone:
            self.data['return_to_authorization'] = True
            self.data['return_data'] = data
            self.save()
            return self.press_change_phone('data')
        if not is_condition:
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='✅ Принять условия', callback_data='accept_conditions')
            keyboard.add(button)
            message1 = '''Ознакомтесь с публичной офертой:
<a href="http://terragent.ru/media/docs/oferta.pdf"> Публичная оферта </a>'''
            message2 = '''А также с политикой конфеденциальности:
<a href="http://terragent.ru/media/docs/policy.pdf"> Политика конфеденциальности </a>
    '''
            self.set_resolver('press_accept_conditions')
            return [(message1, None), (message2, None), ('Если вы согласны с условиями, нажмите кнопку', keyboard)]

    def press_accept_conditions(self, data):
        if data == 'accept_conditions':
            self.user.conditions_accepted = True
            self.user.save()
            self.flush()
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            # help_button = types.KeyboardButton('Помощь')
            # orders_button = types.KeyboardButton('Заказы')
            # account_button = types.KeyboardButton('Аккаунт')
            # purse_button = types.KeyboardButton('Кошелек')
            # keyboard.add(help_button, account_button)
            # keyboard.add(orders_button, purse_button)
            return [('Отлично! Теперь можно продолжить работу с сервисом', None), self.input_help('')]
        else:
            return self.default_resolver(data)

    def press_history(self, text: str):
        histroy, _ = SearchHistory.objects.get_or_create(user=self.user)
        histroy.delete_yestoday()
        message_list = [('Последние запросы:', None)]
        data = histroy.data
        data.reverse()
        for i, item in enumerate(data):
            keyboard = types.InlineKeyboardMarkup()
            text = item['addr_variants']['value']
            button = types.InlineKeyboardButton(text='Повторить', callback_data=f'history_{i}')
            keyboard.add(button)
            message_list.append((text, keyboard))
        if len(message_list) > 1:
            self.set_resolver('press_repeat')
            return message_list
        else:
            self.flush()
            return 'Вы еще ничего не искали...', None

    def press_repeat(self, data: str):
        if 'history' not in data:
            return self.default_resolver(data)
        history_id = int(data.split('_')[1])
        history = SearchHistory.objects.get(user=self.user).data
        history.reverse()
        data = history[history_id]
        self.data = data
        self.save()
        results = self.data['search_results']
        self.set_resolver('press_on_object_variant')
        text = 'Выберите объект:\n'
        buttons = []
        for i, result in enumerate(results):
            text += f'\n<b>Объект {i + 1}:</b>'
            buttons.append(types.InlineKeyboardButton(text=f'Объект {i + 1}', callback_data=f'object_{i}'))
            text += f"\n{result['Кадастровый номер']} - {result['Адрес']}"
            text += f"\nСтатус объекта: {result['Статус объекта']}\n"
        keyboard = types.InlineKeyboardMarkup()
        for button in buttons:
            keyboard.add(button)
        return text, keyboard

    @conditions_accepted_permission
    def press_refill(self, data: str, message=None):
        # self.flush()
        bill_set = Bill.objects.filter(user=self.user, is_payed=False)

        for bill in bill_set:
            logger.debug(f'call update_payment from press_refill for bill: {bill.number}')
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
            return f'У вас уже есть неоплаченный счет:\n {bill.amount / 100} {settings.DEFAULT_CURENCY}', keyboard

        if self.user.email == '':
            self.set_resolver('input_email')
            self.data = {'return_to': 'input_amount', 'return_message': 'Выбирете сумму, либо введите вручную:'}
            self.save()
            return f'Необходимо <b>указать email</b> для получения чеков:', None

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
        yes_button = types.InlineKeyboardButton(text='✅ да', callback_data='y')
        no_button = types.InlineKeyboardButton(text='❌ нет', callback_data='n')
        keyboard.add(yes_button, no_button)
        return f'Пополнить счет на {text} {settings.DEFAULT_CURENCY}?', keyboard

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
            if self.data.get('return_to', None) == 'press_on_service':
                self.set_resolver('press_on_service')
                keyboard2 = types.InlineKeyboardMarkup()
                button2 = types.InlineKeyboardButton(text='Прдолжить оформление',
                                                     callback_data=self.data['return_data'])
                keyboard2.add(button2)
                return [('Сформирован счетна на оплату', keyboard),
                        ('После совершения оплаты, можете продолжить оформление заказа', keyboard2)]
            return f'Сформирован счетна оплату', keyboard

    def input_help(self, text: str):
        # self.flush()
        return '''Для поиска введите <b>адрес</b> или <b>кадастровый номер</b> объекта недвижимости

Например:
<b>Пермь Революции 12 34</b> или <b>59:01:234567:89</b>
''', None

    @conditions_accepted_permission
    def press_purse(self, tet: str):
        # self.flush()
        currency = Curency.objects.get(name=settings.DEFAULT_CURENCY)
        purse, _ = self.user.purse_set.get_or_create(curency=currency)
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text='💳 Пополнить', callback_data='refill')
        keyboard.add(button)
        return f'Баланс: {purse.ammount} {settings.DEFAULT_CURENCY}', keyboard

    def press_my_account(self, text: str):
        # self.flush()
        keyboard = types.InlineKeyboardMarkup()
        top_up_balance = types.InlineKeyboardButton(text='💰 Пополнить баланс', callback_data='refill')
        orders = types.InlineKeyboardButton(text='💼 Заказы', callback_data='orders')
        # referal = types.InlineKeyboardButton(text='Рефералка', callback_data='referal')
        change_email = types.InlineKeyboardButton(text='📧 Изменить email', callback_data='change_email')
        change_phone = types.InlineKeyboardButton(text='☎️ Изменить телефон', callback_data='change_phone')
        feedback = types.InlineKeyboardButton(text='📣 Обратная связь', callback_data='feedback')
        keyboard.add(top_up_balance)
        keyboard.add(orders)
        # keyboard.add(referal)
        keyboard.add(change_email)
        keyboard.add(change_phone)
        keyboard.add(feedback)
        currency = Curency.objects.get(name=settings.DEFAULT_CURENCY)
        purse, _ = self.user.purse_set.get_or_create(curency=currency)
        text = f'''⭐️ <b>Ваш ID</b>: {self.user.telegram_id}
📧 <b>Email</b>: {self.user.email}
☎️ <b>Телефон</b>: {self.user.phone_number}
💰 <b>Баланс</b>: {purse.ammount} {currency.name}
🔎 <b>Количество доступных поисков сегодня</b>: {self.user.searches_remain}
'''
        # Вы с нами с: {self.user.date_joined.strftime('%d.%m.%Y')}

        return text, keyboard

    # @conditions_accepted_permission
    def press_change_email(self, data):
        # self.flush()
        self.set_resolver('input_email')
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text='❌ Отменить', callback_data='cancel_email')
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
            if self.data.get('return_to', None):
                # if self.data['return_to'] == ''
                self.set_resolver(self.data['return_to'])
                keyboard = types.InlineKeyboardMarkup()
                button1 = types.InlineKeyboardButton(text=f'100 {settings.DEFAULT_CURENCY}', callback_data=100)
                button2 = types.InlineKeyboardButton(text=f'250 {settings.DEFAULT_CURENCY}', callback_data=250)
                button3 = types.InlineKeyboardButton(text=f'500 {settings.DEFAULT_CURENCY}', callback_data=500)
                button4 = types.InlineKeyboardButton(text=f'1000 {settings.DEFAULT_CURENCY}', callback_data=1000)
                keyboard.row(button1, button2)
                keyboard.row(button3, button4)
                return f'email изменен на: {self.user.email} \n{self.data["return_message"]}', keyboard
            elif self.data.get('return_to_authorization', None):
                return self.press_authorization(self.data['return_data'])
            else:
                self.flush()
            return f'email изменен на: {self.user.email}', None
        else:
            return 'Это не похоже на правильный email', None

    def press_change_phone(self, data: str):
        self.set_resolver('input_phone')
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton(text='✅ Поделиться', request_contact=True)
        button2 = types.KeyboardButton(text='❌ Отмена')
        keyboard.add(button1)
        keyboard.add(button2)
        return 'Нажмите на кнопку "✅Поделиться" чтобы сообщить нам Ваш номер телефона', keyboard

    def input_phone(self, message: types.Message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        help_button = types.KeyboardButton('🛎 Помощь')
        orders_button = types.KeyboardButton('📝 История')
        account_button = types.KeyboardButton('⭐ Аккаунт')
        purse_button = types.KeyboardButton('💰 Кошелек')
        keyboard.add(help_button, account_button)
        keyboard.add(orders_button, purse_button)
        if not isinstance(message, types.Message):
            if self.user.phone_number != '':
                text = 'Оставим старый номер'
            else:
                text = '''Для работы с сервисом необходимо указать номер телефона'''
            return text, keyboard
        self.user.phone_number = message.contact.phone_number
        self.user.save()
        if self.data.get('return_to_authorization', None):
            returned_obj = [('Спасибо', keyboard)]
            returned_obj.extend(self.press_authorization(self.data['return_data']))
            return returned_obj
        return 'Спасибо', keyboard

    def press_orders(self, data: str):
        # self.flush()
        orders = self.user.order_set.all()
        processed_orders = []
        finished_orders = []
        for order in orders:
            if order.is_finished and (order.date_created - timezone.now()) < \
                    timezone.timedelta(days=settings.RRTELEBOT_ORDERS_AGE):
                finished_orders.append(order)
            else:
                processed_orders.append(order)
        self.set_resolver('press_new_old')
        keyboard = types.InlineKeyboardMarkup()
        new_button = types.InlineKeyboardButton(text=f'В обработке ({len(processed_orders)})',
                                                callback_data='new_orders')
        old_button = types.InlineKeyboardButton(text=f'Исполненные ({len(finished_orders)})',
                                                callback_data='old_orders')
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
        if len(result) == 0:
            return 'У вас пока нет исполненных (обрабатываемых) заказов', None
        return result

    def press_view_order(self, data: str):
        if data.find('order: ') == 0:
            order_id = int(data.split(' ')[1])
            order = Order.objects.get(pk=order_id)
            text = f'Заказ № {order.number} от {order.date_created.strftime("%d.%m.%Y")}\n для адреса {order.address}\n'
            message_list = [(text, None)]
            for exerpt in order.excerpt_set.all():
                if not exerpt.is_delivered:
                    exerpt.check_status()
                if exerpt.is_delivered:
                    status = 'отправлена на почту'
                    keyboard = types.InlineKeyboardMarkup()
                    button = types.InlineKeyboardButton(text='Получить на почту 📬',
                                                        callback_data=f'resend_{exerpt.id}')
                    keyboard.add(button)
                    message_list.append((f'{exerpt.type.name}: {status}\n', keyboard))
                else:
                    status = 'в обработке'
                    message_list.append((f'{exerpt.type.name}: {status}\n', None))
            self.set_resolver('press_resend_docs')
            return message_list
        return None, None

    def press_resend_docs(self, data: str):
        if data.find('resend_') == 0:
            excerpt_id = int(data.split('_')[1])
            excerpt = Excerpt.objects.get(pk=excerpt_id)
            if excerpt.is_delivered:
                excerpt.send_docs()
        self.flush()
        return 'Отправил', None

    def press_feedback(self, data: str):
        keyboard1 = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton(text='🙋 Оставить отзыв', callback_data='review')
        keyboard1.add(button1)
        # keyboard2 = types.InlineKeyboardMarkup(row_width=6)
        button2 = types.InlineKeyboardButton(text='🆘 Сообщить о проблеме', callback_data='report_probem')
        keyboard1.add(button2)
        self.set_resolver('make_feedback')
        return 'Здесь вы можете', keyboard1

    def make_feedback(self, data: str):
        if data == 'review':
            self.set_resolver('input_review')
            return 'Напишите, что Вы думаете о нас', None
        if data == 'report_probem':
            self.set_resolver('input_problem')
            return 'Напишите о проблеме, мы немедленно займемся ее устранением. Обратите внимание, что все ' \
                   '<b>ошибки при поиске объектов регистрируются автоматически</b>, сообщать о них не надо', None

    def input_review(self, text: str):
        Review.objects.create(user=self.user, text=text)
        self.flush()
        return 'Спасибо за Ваш отзыв', None

    def input_problem(self, text: str):
        Ticket.objects.create(user=self.user, description=text)
        self.flush()
        return 'Ваше обращение зарегистрировано. Мы вскоре разберемся с проблемой и уведомим ' \
               'Вас об этом через бота.', None

    def input_adress_string(self, data: str):
        addr_variants = Backend.find_adress(data, self.chat_id)
        if len(addr_variants) == 0:
            return 'Такой адресс не найден, уточните адрес и повторите попытку', None
        else:
            self.data = {'addr_variants': addr_variants[0]}
            self.set_resolver('press_next_on_adsress')
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text=f'Далее', callback_data='next')
            keyboard.row(button)
            text = f'''Адрес распознан как:
<b>{self.data['addr_variants']['value']}</b>
            '''
            return text, keyboard

    def input_cadastr_number(self, data: str):
        try:
            result = Backend.object_by_number(data, self.chat_id)
        except NotFound:
            return 'Ничего не найдено, проверьте правильность ввода. ' \
                   'Если вы ввели все верно, возможно это временная проблема Росреестра', None
        self.data['search_results'] = [result]
        return self.press_on_object_variant('object_0')

    def press_next_on_adsress(self, data: str):
        if self.user.check_free_search():
            if data != 'next':
                return self.default_resolver(data)
            try:
                results = Backend.objects_by_address(self.data['addr_variants'], self.chat_id)
            except (TimeoutError, TemporaryUnavalible):
                Ticket.objects.create(user=self.user,
                                      description=f'Недоступны сервисы при поиске: '
                                                  f'{self.data["addr_variants"]["value"]}')
                logger.debug(f'timeout_error or temporary_unavalible, addr: {self.data["addr_variants"]["value"]}')
                return 'Cервисы Росреестра в настоящий момент недоступны, попробуйте позже...', None
            except:
                Ticket.objects.create(user=self.user,
                                      description=f'Исключение при поиске: {self.data["addr_variants"]["value"]}')
                logger.exception(f'Exeption on search address: {self.data["addr_variants"]["value"]}')
                return 'Низвестная ошибка!!! Мы уже разбираемся с этим. Попробуйте повторить запрос', None

            if len(results) == 0:
                Ticket.objects.create(user=self.user,
                                      description=f'Адрес не найден: {self.data["addr_variants"]["value"]}')
                return 'К сожалению не удалось найти информацию об объекте', None

            self.data['search_results'] = results
            history, _ = SearchHistory.objects.get_or_create(user=self.user)
            history.save_to_history(self.data)
            self.set_resolver('press_on_object_variant')
            text = 'Выберите объект:\n'
            buttons = []
            for i, result in enumerate(results):
                text += f'\n<b>Объект {i + 1}:</b>'
                buttons.append(types.InlineKeyboardButton(text=f'Объект {i + 1}', callback_data=f'object_{i}'))
                text += f"\n{result['Кадастровый номер']} - {result['Адрес']}"
                text += f"\nСтатус объекта: {result['Статус объекта']}\n"

            keyboard = types.InlineKeyboardMarkup()
            for button in buttons:
                keyboard.add(button)
            self.user.increase_search_count()
            return text, keyboard
        else:
            return 'Вы превысили количество бесплатных посиков в день...', None

    def press_on_object_variant(self, data: str):

        if 'object' not in data:
            return self.default_resolver(data)

        object_id = int(data.split('_')[1])

        variant = self.data['search_results'][object_id]
        self.data['choosen_variant'] = variant
        self.set_resolver('press_on_service')
        text = f'<b>Информация по объекту</b>\n'
        for key, value in variant.items():
            text += f'\n<b>{key}</b>: {value}'

        price_list = Service.price_list()
        keyboard = types.InlineKeyboardMarkup()
        for price in price_list:
            button = types.InlineKeyboardButton(
                text=f'{price["short_name"]} за {price["price"]} {settings.DEFAULT_CURENCY}',
                callback_data=f'service_{price["id"]}')
            keyboard.add(button)
        return text, keyboard

    @conditions_accepted_permission
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
            button_ok = types.InlineKeyboardButton(text='✅ Да, все верно, офрмить заказ', callback_data='confirm')
            button_cancel = types.InlineKeyboardButton(text='❌ Отменить', callback_data='cancel')
            keyboard.add(button_ok)
            keyboard.add(button_cancel)
            return f'''Подтвердите ваш заказ:
Адресс: {self.data["choosen_variant"]["Адрес"]}
Кадастровый номер: {self.data["choosen_variant"]["Кадастровый номер"]}
Услуга: {service.name}
Стоимость: {service.get_price()}''', keyboard
# На счете останется: {purse.ammount - service.get_price()}''', keyboard
        else:
            self.data['return_to'] = 'press_on_service'
            self.data['return_data'] = data
            self.save()
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(text='Пополнить счет', callback_data='refill')
            keyboard.add(button)
            return f'У вас на счете: {purse.ammount}, небходимо {service.get_price()}. ' \
                   f'Для продолжения <b>пополните счет</b>', keyboard

    def press_confirm_order(self, data: str):
        if data == 'confirm':
            curency = Curency.objects.get(name__exact=settings.DEFAULT_CURENCY)
            service = Service.objects.get(pk=self.data['service_id'])
            try:
                order = Order.create_order(self.user,
                                           service,
                                           curency,
                                           number=self.data["choosen_variant"]["Кадастровый номер"],
                                           address=self.data["choosen_variant"]["Адрес"])
            except (OrderException, BackendException) as m:
                return m, None
            else:
                self.flush()
                return f'Сформирован заказ № {order.number}\n\nРезультат поступит Вам на e-mail\nБлагодарим🤗\n\n' \
                       f'Найдем что-то еще?😊', None
        elif data == 'cancel':
            self.flush()
            return 'Отменил!', None
