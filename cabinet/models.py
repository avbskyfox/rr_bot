import importlib

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db import transaction
from redis import Redis
from redis.lock import Lock

from notifiers.smtp import send_mail
from rr_backend.backend import Backend
from tinkoff_kassa.models import PaymentModel

redis = Redis()


# Create your models here.


class OrderException(Exception):
    pass


class BackendException(Exception):
    pass


class User(AbstractUser):
    telegram_id = models.CharField(max_length=100, blank=True, db_index=True, unique=True)

    def __str__(self):
        return f'{self.telegram_id}'


class Curency(models.Model):
    class Meta:
        verbose_name = 'Валюта'
        verbose_name_plural = 'Валюты'

    name = models.CharField(max_length=30)
    course = models.FloatField(default=1.0)

    def __str__(self):
        return self.name


class Purse(models.Model):
    class Meta:
        verbose_name = 'Кошелек'
        verbose_name_plural = 'Кошельки'
        unique_together = ['user', 'curency']

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    curency = models.ForeignKey(Curency, on_delete=models.CASCADE, verbose_name='Валюта')
    ammount = models.FloatField(verbose_name='Количество', default=0)
    coefficient = models.FloatField(verbose_name='Скидочный коэфициент', default=1)

    def __str__(self):
        return str(self.user)


class ExcerptType(models.Model):
    class Meta:
        verbose_name = 'Тип выписоки'
        verbose_name_plural = 'Типы выписок'

    name = models.CharField(max_length=100)
    backend_function = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Service(models.Model):
    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    name = models.CharField(max_length=1000, verbose_name='Название услуги')
    short_name = models.CharField(max_length=100, verbose_name='Короткое название')
    button_lable = models.CharField(max_length=20, verbose_name='Кнопка в телегеграм')
    excerpt_types_set = models.ManyToManyField(ExcerptType,
                                               verbose_name='Тип выписки')
    base_price = models.IntegerField(verbose_name='Цена')
    coefficient = models.FloatField(verbose_name='Скидочный коэфициент')

    def get_price(self):
        return self.base_price

    def check_ammount(self, user: User, curency: Curency):
        purse, _ = Purse.objects.get_or_create(user=user, curency=curency)
        return 0 <= purse.ammount - self.base_price

    @classmethod
    def price_list(cls):
        result = list()
        for service in cls.objects.all():
            result.append({'id': service.id, 'name': service.name, 'short_name': service.short_name,
                           'price': service.get_price()})
        result.sort(key=lambda item: item['price'])
        return result

    def serialize(self):
        return {
            'name': self.name,
            'short_name': self.short_name,
            'price': self.get_price(),
        }

    def __str__(self):
        return self.name


class Order(models.Model):
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    # todo поле number нужно переделать
    @property
    def number(self):
        return self.id

    @property
    def is_finished(self):
        exerpt_set = self.excerpt_set.all()
        for exerpt in exerpt_set:
            if not exerpt.is_delivered:
                return True
        return False

    @property
    def address(self):
        return self.excerpt_set.first().address

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, verbose_name='Услуга')
    price = models.IntegerField(verbose_name='Цена', null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    @classmethod
    @transaction.atomic
    def create_order(cls, user: User, service: Service, curency: Curency, **kwargs):
        order = Order.objects.create()
        if not service.check_ammount(user, curency):
            raise OrderException('not enough money')
        for excerpt_type in service.excerpt_types_set.all():
            result = cls._backend_request(excerpt_type, **kwargs)
            if not result['success']:
                raise BackendException(result['message'])
            excerpt = Excerpt.objects.create()
            excerpt.address = kwargs['address']
            excerpt.number = kwargs['number']
            excerpt.type = excerpt_type
            excerpt.user = user
            excerpt.order = order
            excerpt.foreign_number = result['number']
            excerpt.row_data = result['raw']
            excerpt.save()
            from .tasks import update_exerpt_status
            update_exerpt_status.delay(excerpt.id, user.telegram_id)
        purse = user.purse_set.filter(curency=curency).first()
        order.user = user
        order.service = service
        order.price = service.base_price * service.coefficient * purse.coefficient
        order.save()
        purse.ammount = purse.ammount - order.price
        purse.save()
        return order

    @staticmethod
    def _backend_request(excerpt_type: ExcerptType, **kwargs):
        module = importlib.import_module(settings.BACKEND)
        func = getattr(module, excerpt_type.backend_function)
        return func(**kwargs)

    def get_info(self):
        return {
            'number': self.number,
            'excerpts': [
                {
                    'address': excerpt.address,
                    'number': excerpt.number,
                    'date': excerpt.date_created.strftime('%d.%m.%Y'),
                    'name': excerpt.type.name,
                    'delivered': excerpt.is_delivered,
                    'excerpt': excerpt
                }
                for excerpt in self.excerpt_set.all()
            ]
        }

    def __str__(self):
        return str(self.number)


class Excerpt(models.Model):
    class Meta:
        verbose_name = 'Выписка'
        verbose_name_plural = 'Выписки'

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    type = models.ForeignKey(ExcerptType, on_delete=models.SET_NULL, null=True, verbose_name='Тип выписки')
    address = models.CharField(max_length=1024, verbose_name='Адрес объекта')
    number = models.CharField(max_length=20, verbose_name='Кадастровый номер объекта')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    foreign_number = models.CharField(max_length=128, verbose_name='Номер выписки в сервисе партнера')
    row_data = models.JSONField(max_length=1024, verbose_name='Сырые данные ответа партнера', null=True, default=None)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, verbose_name='Заказ')
    is_ready = models.BooleanField(default=False, verbose_name='Готова к отправке?')
    is_delivered = models.BooleanField(default=False, verbose_name='Отправлена?')

    def check_status(self):
        with Lock(redis, name=f'exerpt_{self.id}'):
            result = Backend.get_doc_status(self.foreign_number)
            if result['status'] == 'ready':
                self.is_ready = True
                self.send_docs()
                self.save()
                return True

    def download_docs(self):
        return Backend.download_doc(self.foreign_number)

    def send_docs(self):
        send_mail(to_addr=self.user.email,
                  subject=f'Выписки к заказу № {self.order.number}',
                  text='Ваши выписки готовы',
                  files=self.download_docs())

    @sync_to_async
    def async_send_docs(self):
        return self.send_docs()

    @sync_to_async
    def async_check_status(self):
        return self.check_status()

    def __str__(self):
        return f'{self.order_id}_{self.type_id}'


class Bill(models.Model):
    class Meta:
        verbose_name = 'Счет'
        verbose_name_plural = 'Счета'

    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, db_index=True, verbose_name='Пользователь')
    curency = models.ForeignKey(Curency, on_delete=models.DO_NOTHING, verbose_name='Внутренняя валюта')
    amount = models.IntegerField(verbose_name='Кол-во внутренней валюты')
    price = models.IntegerField(verbose_name='Цена в копейках')
    payment = models.ForeignKey(PaymentModel, on_delete=models.SET_NULL, null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    is_payed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user} - {self.amount} {self.curency}'

    def create_payment(self):
        params = {
            "Amount": str(self.price),
            "OrderId": str(self.id),
            "Description": f"Покупка внутренней валюты в колиестве: {self.amount}",
            "Receipt": {
                "Email": self.user.email,
                "Taxation": "osn",
                "Items": [
                    {
                        "Name": "1",
                        "Price": self.price,
                        "Quantity": 1.00,
                        "Amount": self.price,
                        "PaymentMethod": "full_prepayment",
                        "PaymentObject": "service",
                        "Tax": "vat10"
                    }
                ]
            }
        }
        self.payment = PaymentModel.create_payment(params)
        self.save()

    def update_payment(self):
        with Lock(redis, name=f'bill_{self.id}', timeout=10):
            if self.payment is not None:
                self.payment.get_state()
                if self.payment.is_confirmed:
                    self.is_payed = True
                    self.save()
                    purse = self.user.purse_set.get(curency=self.curency)
                    purse.ammount += self.amount / 100
                    purse.save()
                if self.payment.is_canceled:
                    self.delete()
            else:
                self.delete()

    def cancel_payment(self):
        self.payment.cancel()
        self.save()
