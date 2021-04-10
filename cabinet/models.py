from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import importlib
from django.db import transaction


# Create your models here.


class OrderException(Exception):
    pass


class BackendException(Exception):
    pass


class User(AbstractUser):
    telegram_id = models.CharField(max_length=100, blank=True, db_index=True, unique=True)


class Curency(models.Model):
    class Meta:
        verbose_name = 'Валюта'
        verbose_name_plural = 'Валюты'

    name = models.CharField(max_length=30)

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
    price = models.IntegerField(verbose_name='Цена')
    coefficient = models.FloatField(verbose_name='Скидочный коэфициент')

    def check_ammount(self, user: User, curency: Curency):
        purse, _ = Purse.objects.get_or_create(user=user, curency=curency)
        return 0 <= purse.ammount - self.price

    @classmethod
    def price_list(cls):
        result = list()
        for service in cls.objects.all():
            result.append({'service': service.short_name, 'price': service.price})
        result.sort(key=lambda item: item['price'])
        return result

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

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, verbose_name='Услуга')
    price = models.IntegerField(verbose_name='Цена', null=True)

    @classmethod
    @transaction.atomic()
    def create_order(cls, user: User, service: Service, curency: Curency, **kwargs):
        order = Order.objects.create()
        if not service.check_ammount(user, curency):
            raise OrderException('not enough money')
        for excerpt_type in service.excerpt_types_set.all():
            result = cls._backend_request(excerpt_type, **kwargs)
            print(result)
            if not result['success']:
                raise BackendException(result['message'])
            excerpt = Excerpt.objects.create()
            excerpt.address = kwargs['address']
            excerpt.number = kwargs['number']
            excerpt.type = excerpt_type
            excerpt.user = user
            excerpt.order = order
            excerpt.save()
        purse = user.purse_set.filter(curency=curency).first()
        order.user = user
        order.service = service
        order.price = service.price * service.coefficient * purse.coefficient
        order.save()
        purse.ammount = purse.ammount - order.price
        purse.save()
        return order

    @staticmethod
    def _backend_request(excerpt_type: ExcerptType, **kwargs):
        module = importlib.import_module(settings.BACKEND)
        func = getattr(module, excerpt_type.backend_function)
        return func(**kwargs)

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
    date_created = models.DateField(auto_now_add=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, verbose_name='Заказ')

    def __str__(self):
        return f'{self.order_id}_{self.type_id}'
