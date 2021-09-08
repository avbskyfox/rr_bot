from celery import shared_task
from telebot import TeleBot
from cabinet.models import Excerpt
from django.conf import settings

bot = TeleBot(token=settings.TELEGRAM_API_TOKEN)


@shared_task(default_retry_delay=3600, max_retries=168)
def update_exerpt_status(exerpt_id, chat_id):
    exerpt = Excerpt.objects.get(pk=exerpt_id)
    exerpt.check_status()
    if not exerpt.is_ready:
        update_exerpt_status.retry()
    else:
        bot.send_message(chat_id, f'{exerpt.type} для {exerpt.address} отправлена Вам на почту')
        exerpt.is_delivered=True
        exerpt.save()
