from django.db import models
from cabinet.models import User


class Dialog(models.Model):
    class Meta:
        verbose_name = 'Диалог'

    telegram_id = models.OneToOneField(User, to_field='telegram_id',
                                       on_delete=models.CASCADE,
                                       verbose_name='Пользователь',
                                       db_index=True,
                                       primary_key=True)
    step = models.IntegerField(verbose_name='шаг', default=0)
    data = models.JSONField(verbose_name='данные', default=dict)

    def flush(self):
        self.step = 0
        self.data = {}
        self.save()
