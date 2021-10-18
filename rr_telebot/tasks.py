from celery import shared_task
from django.conf import settings
from telebot import TeleBot

from cabinet.models import Bill

bot = TeleBot(token=settings.TELEGRAM_API_TOKEN)
admin_bot = TeleBot(settings.NOTIFIER_BOT_TOKEN)
group_id = '-716316171'


@shared_task(default_retry_delay=10, max_retries=12)
def update_bill_status(bill_id, chat_id):
    bill = Bill.objects.get(pk=bill_id)
    bill.update_payment()
    if not bill.is_payed:
        update_bill_status.retry()
    else:
        bot.send_message(chat_id, f'На ваш сет начисленно {int(bill.amount / 100)} RUR')


@shared_task()
def send_to_adm_group(text):
    admin_bot.send_message(group_id, text)
