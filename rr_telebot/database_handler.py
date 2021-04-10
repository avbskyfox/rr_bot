import os

import django

os.environ["DJANGO_SETTINGS_MODULE"] = 'rosreestr.settings'
django.setup()
from django.conf import settings
from asgiref.sync import sync_to_async
from cabinet.models import *
from rr_telebot.models import *


DEFAULT_CURENCY = getattr(settings, 'DEFAULT_CURENCY', 'RUR')


class WrongStep(Exception):
    pass


@sync_to_async
def create_user(username: str, telegram_id: int):
    user, created = User.objects.get_or_create(username=username, telegram_id=telegram_id)
    if created:
        user.save()
    return user, created


def get_or_create_purse(user: User):
    curency = Curency.objects.get(name__exact=DEFAULT_CURENCY)
    purse, _ = Purse.objects.get_or_create(curency=curency, user=user)
    return purse


@sync_to_async
def new_dialog(telegram_id: int):
    dialog, created = Dialog.objects.get_or_create(pk=telegram_id)
    if not created:
        dialog.flush()
    return dialog


@sync_to_async
def step2_db(dialog: Dialog, number: str, address: str):
    dialog.data['number'] = number
    dialog.data['address'] = address
    dialog.step = 3
    dialog.save()


@sync_to_async
def step3_db(telegram_id: int):
    try:
        dialog = Dialog.objects.get(pk=telegram_id)
    except Dialog.DoesNotExist:
        raise WrongStep
    if dialog.step != 3:
        raise WrongStep
    purse = get_or_create_purse(dialog.telegram_id)
    dialog.step = 4
    dialog.save()
    return {
        'address': dialog.data['address'],
        'number': dialog.data['number'],
        'curency': purse.curency.name,
        'ammount': purse.ammount,
        'services': [service for service in Service.objects.all()]
    }


@sync_to_async
def get_curent_step(telegram_id: int):
    dialog, _ = Dialog.objects.get_or_create(telegram_id=telegram_id)
    return dialog.step


@sync_to_async
def step4_db(telegram_id: int, service_id: int):
    try:
        dialog = Dialog.objects.get(pk=telegram_id)
    except Dialog.DoesNotExist:
        raise WrongStep
    if dialog.step != 4:
        raise WrongStep
    dialog.step = 5
    dialog.data['service']: service_id
    dialog.save()
    purse = get_or_create_purse(dialog.telegram_id)
    service = Service.objects.get(pk=service_id)
    return {
        'address': dialog.data['address'],
        'number': dialog.data['number'],
        'curency': purse.curency.name,
        'ammount': purse.ammount,
        'service': service
    }

# db_file = os.path.abspath('db.sqlite3')
# from rr_telebot.tortoise_models import *
# from tortoise import Tortoise
# @asynccontextmanager
# async def db_connection():
#     await Tortoise.init(
#         db_url=f'sqlite://{db_file}',
#         modules={'models': ['rr_telebot.tortoise_models']}
#     )
#     try:
#         yield None
#     finally:
#         await Tortoise.close_connections()
#
#
# def create_user(username: str, telegram_id: int):
#     async with db_connection():
#         user, created = await User.get_or_create(username=username, telegram_id=telegram_id)
#         if created:
#             await user.save()
#         return user, created
#
#
# async def new_dialog(telegram_id: int):
#     async with db_connection():
#         user = await User.get(telegram_id=telegram_id)
#         dialog, created = await Dialog.get_or_create(telegram_id=user.id)
#         if not created:
#             await dialog.flush()
#         return dialog
#
#
# async def step2(dialog: Dialog, number, address):
#     dialog.data['number'] = number
#     dialog.data['address'] = address
#     async with db_connection():
#         await dialog.save()
