from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class User(AbstractUser):
    telegram_id = models.CharField(max_length=100, blank=True)


class Curencies(models.Model):
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

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    currency = models.ForeignKey(Curencies, on_delete=models.CASCADE, verbose_name='Валюта')
    ammount = models.FloatField(verbose_name='Количество')
    coefficient = models.FloatField(verbose_name='Скидочный коэфициент')

    def __str__(self):
        return str(self.user)
