from celery import shared_task
from django.conf import settings
from telebot import TeleBot

from cabinet.models import Bill

bot = TeleBot(token=settings.TELEGRAM_API_TOKEN)


@shared_task(default_retry_delay=5, max_retries=8)
def update_bill_status(bill_id, chat_id):
    bill = Bill.objects.get(pk=bill_id)
    bill.update_payment()
    if not bill.is_payed:
        update_bill_status.retry()
    else:
        bot.send_message(chat_id, f'На ваш сет начисленно {int(bill.amount / 100)} RUR')
