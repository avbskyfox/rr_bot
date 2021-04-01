import telebot
import json
from rr_backend.test_backend import TestBackend
import os
import django
from telebot import apihelper
from loguru import logger

apihelper.ENABLE_MIDDLEWARE = True
os.environ["DJANGO_SETTINGS_MODULE"] = 'rosreestr.settings'
django.setup()
from cabinet.models import User, Service, Curency, Purse, Order, OrderException, BackendException
from rr_telebot.models import Dialog

backend = TestBackend()
bot = telebot.TeleBot('1715391513:AAEkJQfptLEOf-veUqgpLlKitQjKliUPRrs')


def checker_func(call: telebot.types.CallbackQuery, step: int) -> bool:
    dialog, _ = Dialog.objects.get_or_create(pk=call.from_user.id)
    return dialog.step == step


class StepCheckersPooll:
    def __getitem__(self, item):
        return lambda call: checker_func(call, item)


check_step = StepCheckersPooll()


@bot.middleware_handler(update_types=['message'])
def registration_check(bot_instance: telebot.TeleBot, message: telebot.types.Message):
    logger.debug(f"{message.from_user.id} write: {message.text}")
    user, is_created = User.objects.get_or_create(telegram_id=message.from_user.id)
    user.username = message.from_user.id
    user.save()
    if is_created:
        user.username = message.from_user.id
        user.save()
        logger.debug(f"user {user.username} created")
        keyboard = telebot.types.InlineKeyboardMarkup()
        url = telebot.types.InlineKeyboardButton(text='Сайт', url='http://127.0.0.1:8000')
        keyboard.add(url)
        bot.send_message(message.chat.id, 'Вы только что были зарегистрированы на сайте,'
                                          ' нажмите кнопку чтобы перейти на сайт и закончить'
                                          'регистрацию', reply_markup=keyboard)


@bot.message_handler(content_types=['text'], regexp="^(\d\d):(\d\d):*")
def address_by_number_handler(message: telebot.types.Message):
    result = backend.address_by_number(message.text)
    logger.debug(f'beckend response: {result}')
    dialog, _ = Dialog.objects.get_or_create(pk=message.from_user.id)
    dialog.flush()
    if result['success']:
        dialog.step = 2
        dialog.data['number'] = result['data']['number']
        dialog.data['address'] = result['data']['address']
        dialog.save()
        keyboard = telebot.types.InlineKeyboardMarkup()
        button = telebot.types.InlineKeyboardButton('Продолжить', callback_data='continue')
        keyboard.add(button)
        bot.send_message(message.chat.id,
                         f"{result['data']['address']}, "
                         f"кадастровый номер: {result['data']['number']}",
                         reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, 'К сожалению ничего не найдено')


@bot.message_handler(content_types=['text'], regexp=".* .* .*")
def number_by_address_handler(message):
    result = backend.number_by_address(message.text)
    logger.debug(f'beckend response: {result}')
    if result['success'] == 1:
        dialog, _ = Dialog.objects.get_or_create(pk=message.from_user.id)
        dialog.flush()
        dialog.step = 2
        dialog.data['address'] = result['data']['address']
        dialog.data['number'] = result['data']['number']
        dialog.save()
        keyboard = telebot.types.InlineKeyboardMarkup()
        button = telebot.types.InlineKeyboardButton('Продолжить', callback_data='continue')
        keyboard.add(button)
        bot.send_message(message.chat.id,
                         f"{result['data']['address']}, "
                         f"кадастровый номер: {result['data']['number']}",
                         reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, 'К сожалению ничего не найдено')


@bot.callback_query_handler(func=check_step[2])
def continue_handler(call: telebot.types.CallbackQuery):
    dialog, _ = Dialog.objects.get_or_create(pk=call.from_user.id)
    keyboard = telebot.types.InlineKeyboardMarkup()
    phrase = f"Для объекта: {dialog.data['address']}, кадастровый номер: {dialog.data['number']}\n" \
             f"Выбирете вариант услуги:\n"

    for i, serice in enumerate(Service.objects.all()):
        button = telebot.types.InlineKeyboardButton(i + 1, callback_data=serice.id)
        keyboard.row(button)
        phrase += f"Вариант {i + 1}: {serice.name}\n"

    bot.send_message(call.message.chat.id, phrase, reply_markup=keyboard)
    dialog.step = 3
    dialog.save()


@bot.callback_query_handler(func=check_step[3])
def confirm_step(call: telebot.types.CallbackQuery):
    dialog, _ = Dialog.objects.get_or_create(telegram_id=call.from_user.id)
    dialog.step = 4
    service = Service.objects.get(pk=call.data)
    dialog.data['service'] = service.id
    dialog.save()
    phrase = service.name
    keyboard = telebot.types.InlineKeyboardMarkup()
    yes = telebot.types.InlineKeyboardButton('ДА', callback_data='__yes__')
    no = telebot.types.InlineKeyboardButton('НЕТ', callback_data='__no__')
    keyboard.add(yes, no)
    bot.send_message(call.message.chat.id, f"Для объекта {dialog.data['address']} вы заказываете {phrase}",
                     reply_markup=keyboard)


@bot.callback_query_handler(func=check_step[4])
def make_query(call: telebot.types.CallbackQuery):
    dialog, _ = Dialog.objects.get_or_create(telegram_id=call.from_user.id)
    if call.data == '__yes__' or call.data == 'continue':
        service = Service.objects.get(pk=dialog.data['service'])
        curency = Curency.objects.get(name__exact='RUR')
        purse, _ = Purse.objects.get_or_create(user=dialog.telegram_id, curency=curency)
        if not service.check_ammount(dialog.telegram_id, curency):
            keyboard = telebot.types.InlineKeyboardMarkup()
            fill_url = telebot.types.InlineKeyboardButton(text='Пополнить', url='http://127.0.0.1')
            ok = telebot.types.InlineKeyboardButton(text='Продолжить', callback_data='continue')
            keyboard.row(fill_url)
            keyboard.row(ok)
            bot.send_message(call.message.chat.id,
                             f"На вашем счете {purse.ammount} {curency.name}, "
                             f"сумма заказа: {service.price} {curency.name}.\n"
                             f"Для продолжени пополните счет",
                             reply_markup=keyboard)
        else:
            logger.debug(f'trying to create order for {dialog.telegram_id}, {service}, {curency}')
            try:
                order = Order.create_order(dialog.telegram_id,
                                           service,
                                           curency,
                                           address=dialog.data['address'],
                                           number=dialog.data['number'])
                bot.send_message(call.message.chat.id, f"Создан заказ № {order.number}")
            except OrderException as m:
                logger.error(m)
            except BackendException as m:
                logger.error(m)
                bot.send_message(call.message.chat.id, f"Извините, сервис не может выполнить запрос")
            dialog.flush()
    else:
        dialog.flush()


@bot.callback_query_handler(func=check_step[0])
def fluched_dialog(call: telebot.types.CallbackQuery):
    bot.send_message(call.message.chat.id, f'Что бы начать введите кадастровый номер или адресс объекта')


@bot.message_handler(content_types=['text'])
def greeting_message(message):
    bot.send_message(message.chat.id, f'Что бы начать введите кадастровый номер или адресс объекта')


@logger.catch()
def run():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    run()
