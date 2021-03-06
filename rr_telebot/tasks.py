from celery import shared_task
from django.conf import settings
from telebot import TeleBot
from loguru import logger

from cabinet.models import Bill

bot = TeleBot(token=settings.TELEGRAM_API_TOKEN)
admin_bot = TeleBot(settings.NOTIFIER_BOT_TOKEN)
group_id = settings.ADMIN_GROUP_ID


@shared_task(default_retry_delay=10, max_retries=24)
def update_bill_status(bill_id, chat_id):
    bill = Bill.objects.get(pk=bill_id)
    logger.debug(f'call update_payment from celery task update_bill_status for bill: {bill.number}')
    bill.update_payment()
    if not bill.is_payed:
        update_bill_status.retry()


@shared_task(default_retry_delay=30, max_retries=3)
def notify_user(user_id, text):
    bot.send_message(user_id, text)


@shared_task(default_retry_delay=30, max_retries=3)
def send_to_adm_group(text):
    admin_bot.send_message(group_id, text)
