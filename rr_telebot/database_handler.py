import os

import django

os.environ["DJANGO_SETTINGS_MODULE"] = 'rosreestr.settings'
django.setup()
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
        curency = Curency.objects.get(name__exact=DEFAULT_CURENCY)
        purse, _ = Purse.objects.get_or_create(curency=curency, user=user)
        user.save()
    return user, created


def get_or_create_purse(user: User, curency: Curency = None):
    if curency is None:
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
def save_dadata_varinants(telegram_id: int, dadata):
    dialog, created = Dialog.objects.get_or_create(pk=telegram_id)
    if not created:
        dialog.flush()
    dialog.dadata = dadata
    dialog.step = 1
    dialog.save()


@sync_to_async
def save_data_to_dialog(telegram_id, data):
    dialog, created = Dialog.objects.get_or_create(pk=telegram_id)
    dialog.data = data
    dialog.save()


@sync_to_async
def pick_address(telegram_id: int, variant: int):
    try:
        dialog = Dialog.objects.get(pk=telegram_id)
    except Dialog.DoesNotExist:
        raise WrongStep
    if dialog.step != 1:
        raise WrongStep
    dialog.dadata = dialog.dadata[variant]
    dialog.address = dialog.dadata['value']
    dialog.step = 2
    dialog.save()
    return dialog


# @sync_to_async
# def step3_db(telegram_id: int):
#     try:
#         dialog = Dialog.objects.get(pk=telegram_id)
#     except Dialog.DoesNotExist:
#         raise WrongStep
#     if dialog.step != 3:
#         raise WrongStep
#     purse = get_or_create_purse(dialog.telegram_id)
#     dialog.step = 4
#     dialog.save()
#     return {
#         'address': dialog.address,
#         'number': dialog.number,
#         'curency': purse.curency.name,
#         'ammount': purse.ammount,
#         'services': [service for service in Service.objects.all()]
#     }


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
    dialog.curency = Curency.objects.get(name__exact=DEFAULT_CURENCY)
    purse = get_or_create_purse(dialog.telegram_id, dialog.curency)
    service = Service.objects.get(pk=service_id)
    dialog.service = service
    dialog.save()
    return {
        'address': dialog.address,
        'number': dialog.number,
        'curency': purse.curency.name,
        'ammount': purse.ammount,
        'service': service
    }


@sync_to_async
def get_dialog(telegram_id: int):
    dialog = Dialog.objects.get(pk=telegram_id)
    return dialog


@sync_to_async
def save_dialog(dialog: Dialog):
    dialog.save()


@sync_to_async
def create_order(telegram_id: int):
    dialog = Dialog.objects.get(pk=telegram_id)
    try:
        order = Order.create_order(dialog.telegram_id, dialog.service, dialog.curency, number=dialog.number,
                                   address=dialog.address)
        return True, order
    except OrderException as m:
        return False, None
    except BackendException as m:
        return False, None


@sync_to_async
def get_price_list():
    result = Service.price_list()
    return result
