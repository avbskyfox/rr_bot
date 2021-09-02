from celery import shared_task
from cabinet.models import Bill
from telebot import TeleBot

bot = TeleBot(token='1715391513:AAEkJQfptLEOf-veUqgpLlKitQjKliUPRrs')


@shared_task(default_retry_delay=5, max_retries=8)
def update_bill_status(bill_id, chat_id):
    bill = Bill.objects.get(pk=bill_id)
    bill.update_payment()
    if not bill.is_payed:
        update_bill_status.retry()
    else:
        bot.send_message(chat_id, f'На ваш сет начисленно {int(bill.amount/100)} RUR')
