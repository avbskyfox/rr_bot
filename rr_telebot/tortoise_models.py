from datetime import datetime

from tortoise import fields
from tortoise.models import Model


class User(Model):
    class Meta:
        table = 'cabinet_user'

    username = fields.CharField(max_length=255, index=True)
    telegram_id = fields.IntField(unique=True)
    password = fields.CharField(max_length=255, default='')
    is_superuser = fields.BooleanField(default=False)
    first_name = fields.CharField(max_length=255, default='')
    last_name = fields.CharField(max_length=255, default='')
    email = fields.CharField(max_length=255, default='')
    is_staff = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
    date_joined = fields.DatetimeField(default=datetime.now)

    def __str__(self):
        return self.username


class Dialog(Model):
    class Meta:
        table = 'rr_telebot_dialog'
        verbose_name = 'Диалог'

    telegram_id: fields.OneToOneRelation[User] = fields.OneToOneField('models.User',
                                                                      to_field='id',
                                                                      on_delete=fields.CASCADE,
                                                                      index=True,
                                                                      pk=True)
    step = fields.IntField(verbose_name='шаг', default=0)
    data = fields.JSONField(verbose_name='данные', default=dict)

    async def flush(self):
        self.step = 0
        self.data = dict()
        await self.save()
