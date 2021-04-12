from django.db import models
from cabinet.models import User, Service, Curency
from django.core import serializers


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
