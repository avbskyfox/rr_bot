import os

import django



os.environ["DJANGO_SETTINGS_MODULE"] = 'rosreestr.settings'
django.setup()

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
def pick_service(telegram_id: int, service_id: int):
    try:
        dialog = Dialog.objects.get(pk=telegram_id)
    except Dialog.DoesNotExist:
        raise WrongStep
    dialog.step = 4
    dialog.curency = Curency.objects.get(name__exact=DEFAULT_CURENCY)
    get_or_create_purse(dialog.telegram_id, dialog.curency)
    service = Service.objects.get(pk=service_id)
    dialog.service = service
    dialog.save()
    return service.check_ammount(dialog.telegram_id, dialog.curency), dialog


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
        return False, m
    except BackendException as m:
        return False, m


@sync_to_async
def orders_info(telegram_id: int):
    return [
        order.get_info() for order in User.objects.get(telegram_id=telegram_id).order_set.all()
    ]


@sync_to_async
def get_account_info(telegram_id: int):
    user = User.objects.get(telegram_id=telegram_id)
    return {
        'Ваш ID': user.telegram_id,
        'Вы с нами с': user.date_joined.strftime('%d.%m.%Y'),
        'Баланс': user.purse_set.get(curency__name=settings.DEFAULT_CURENCY).ammount,
    }


@sync_to_async
def update_email(telegram_id: int, email: str):
    user = User.objects.get(telegram_id=telegram_id)
    user.email = email
    user.save()


@sync_to_async
def get_price_list():
    result = Service.price_list()
    return result


@sync_to_async
def start_balance_dialog(telegram_id: int):
    dialog, _ = BalanceDialog.objects.get_or_create(pk=telegram_id)
    if dialog.step == 0:
        dialog.step = 1
        dialog.save()
        return {'is_new': True}
    else:
        if dialog.bill:
            return {'is_new': False,
                    'payment_url': 'http://127.0.0.1',
                    'price': '',
                    'inner_amount': '',
                    'inner_curency': ''}
        else:
            dialog.step = 1
            dialog.save()
            return {'is_new': True}


@sync_to_async
def check_step1(telegram_id: int):
    dialog, _ = BalanceDialog.objects.get_or_create(pk=telegram_id)
    return dialog.step == 1


@sync_to_async
def balance_dialog_step1(telegram_id: int, amount):
    dialog, _ = BalanceDialog.objects.get_or_create(pk=telegram_id)
    dialog.step = 2
    curency = Curency.objects.get(name=settings.DEFAULT_CURENCY)
    dialog.bill = Bill.objects.create(user=dialog.user,
                                      curency=curency,
                                      amount=int(amount*100),
                                      price=amount*curency.course)
    dialog.save()


@sync_to_async
def save_balance_dialog(dialog: BalanceDialog):
    dialog.save()
