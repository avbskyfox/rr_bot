from telebot import TeleBot
from django.conf import settings

bot = TeleBot(settings.NOTIFIER_BOT_TOKEN)
# bot = TeleBot('2062494929:AAGn_K_uAIO33QKtsQKK69IHVg4sAkI7hMM')

group_id = '-716316171'


def send_message(text):
    bot.send_message(group_id, text)


if __name__ == '__main__':
    send_message('test')