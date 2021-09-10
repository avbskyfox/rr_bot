from aiogram import Bot, Dispatcher, executor, types
from django.conf import settings
from redis import Redis
from asyncio import sleep
from loguru import logger
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

bot = TeleBot(token=settings.TELEGRAM_API_TOKEN)
redis = Redis(settings.PROGRESS_NOTIFIER_REDIS_HOST,
              settings.PROGRESS_NOTIFIER_REDIS_PORT,
              settings.PROGRESS_NOTIFIER_REDIS_DB)


class ProgressNotifier:
    def __init__(self, chat_id):
        self._chat_id = chat_id

    def send_message(self, text):
        old_message_id = redis.get(self._chat_id)
        if old_message_id:
            try:
                message = bot.edit_message_text(text, self._chat_id, old_message_id)
                redis.set(self._chat_id, message.message_id)
            except ApiTelegramException:
                self.delete_last_message()
                message = bot.send_message(self._chat_id, text)
                redis.set(self._chat_id, message.message_id)
        else:
            message = bot.send_message(self._chat_id, text)
            redis.set(self._chat_id, message.message_id)

    def delete_last_message(self):
        old_message_id = redis.get(self._chat_id)
        if old_message_id:
            try:
                bot.delete_message(self._chat_id, old_message_id)
            except ApiTelegramException:
                pass
            finally:
                redis.delete(self._chat_id)
