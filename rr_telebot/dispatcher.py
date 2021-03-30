import telebot
import json
from rr_telebot.test_backend import TestBackend
import os
import django
from telebot import apihelper

apihelper.ENABLE_MIDDLEWARE = True
os.environ["DJANGO_SETTINGS_MODULE"] = 'rosreestr.settings'
django.setup()
from cabinet.models import User
from rr_telebot.models import Dialog

backend = TestBackend()
bot = telebot.TeleBot('1715391513:AAEkJQfptLEOf-veUqgpLlKitQjKliUPRrs')


def checker_func(call: telebot.types.CallbackQuery, step: int) -> bool:
    dialog, _ = Dialog.objects.get_or_create(pk=call.from_user.id)
    print(dialog.step == step)
    return dialog.step == step


class StepCheckersPooll:
    def __getitem__(self, item):
        return lambda call: checker_func(call, item)


check_step = StepCheckersPooll()


@bot.middleware_handler(update_types=['message'])
def registration_check(bot_instance: telebot.TeleBot, message: telebot.types.Message):
    print(message.from_user.id)
    user, is_created = User.objects.get_or_create(telegram_id=message.from_user.id)
    user.username = message.from_user.id
    user.save()
    if is_created:
        user.username = message.from_user.id
        user.save()
        keyboard = telebot.types.InlineKeyboardMarkup()
        url = telebot.types.InlineKeyboardButton(text='Сайт', url='http://127.0.0.1:8000')
        keyboard.add(url)
        bot.send_message(message.chat.id, 'Вы только что были зарегистрированы на сайте,'
                                          ' нажмите кнопку чтобы перейти на сайт и закончить'
                                          'регистрацию', reply_markup=keyboard)


@bot.message_handler(content_types=['text'], regexp="^(\d\d):(\d\d):*")
def address_by_number_handler(message: telebot.types.Message):
    result = backend.address_by_number(message.text)
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
    print(result)
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
    button1 = telebot.types.InlineKeyboardButton('ВАРИАНТ1',
                                                 callback_data=1)
    button2 = telebot.types.InlineKeyboardButton('ВАРИАНТ2',
                                                 callback_data=2)
    button3 = telebot.types.InlineKeyboardButton('ОБА ВАРИАНТА', callback_data=3)
    keyboard.row(button1)
    keyboard.row(button2)
    keyboard.row(button3)
    bot.send_message(call.message.chat.id, f"Для объекта: {dialog.data['address']}, кадастровый номер:"
                                      f"{dialog.data['number']}\n"
                                      f"Выбирете вариант выписки:\n"
                                      f"Вариант1: выписка бла бла бла за 60р\n"
                                      f"Вариант2: выписка бло бло бло 60р\n"
                                      f"Вариант3: обе выписки за 100р", reply_markup=keyboard)
    dialog.step = 3
    dialog.save()


@bot.callback_query_handler(func=check_step[3])
def confirm_step(call: telebot.types.CallbackQuery):
    print('step 3')
    print(call)
    dialog, _ = Dialog.objects.get_or_create(telegram_id=call.from_user.id)
    data = json.loads(call.data)
    dialog.step = 4
    if data == 1:
        dialog.data['type'] = 1
        dialog.save()
        phrase = "выписка бла бла бла за 60р"
    elif data == 2:
        dialog.data['type'] = 2
        dialog.save()
        phrase = "выписка бло бло бло за 60р"
    elif data == 3:
        dialog.data['type'] = 3
        dialog.save()
        phrase = "обе выписки за 100р"
    keyboard = telebot.types.InlineKeyboardMarkup()
    yes = telebot.types.InlineKeyboardButton('ДА', callback_data='__yes__')
    no = telebot.types.InlineKeyboardButton('НЕТ', callback_data='__no__')
    keyboard.add(yes, no)
    bot.send_message(call.message.chat.id, f"Для объекта {dialog.data['address']} вы заказываете {phrase}", reply_markup=keyboard)


@bot.callback_query_handler(func=check_step[4])
def make_query(call: telebot.types.CallbackQuery):
    print('step 4')
    print(call)
    dialog, _ = Dialog.objects.get_or_create(telegram_id=call.from_user.id)
    if call.data == '__yes__':
        if dialog.data['type'] == 1:
            result = backend.get_doc_type1(dialog.data['number'])
            if result['success'] == 1:
                bot.send_message(call.message.chat.id, 'Вы заказали выписку 1')
        elif dialog.data['type'] == 2:
            result = backend.get_doc_type2(dialog.data['number'])
            if result['success'] == 1:
                bot.send_message(call.message.chat.id, 'Вы заказали выписку 2')
        elif dialog.data['type'] == 3:
            result = backend.get_doc_type1(dialog.data['number'])
            if result['success'] == 1:
                bot.send_message(call.message.chat.id, 'Вы заказали выписку 1')
            result = backend.get_doc_type2(dialog.data['number'])
            if result['success'] == 1:
                bot.send_message(call.message.chat.id, 'Вы заказали выписку 2')
    dialog.flush()


@bot.message_handler(content_types=['text'])
def greeting_message(message):
    print(message.text)
    bot.send_message(message.chat.id, f'Что бы начать введите кадастровый номер или адресс объекта')


print('Start bot')
bot.polling(none_stop=True)
