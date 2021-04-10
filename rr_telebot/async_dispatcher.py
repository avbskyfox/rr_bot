import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from loguru import logger

from rr_backend.test_backend import async_backend as backend
from rr_telebot.database_handler import create_user, new_dialog, step2_db, step3_db, get_curent_step, step4_db
from rr_telebot.template_message import *

API_TOKEN = os.environ.get('API_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)


class RegisterUserMiddleware(BaseMiddleware):
    @staticmethod
    async def on_process_message(message: types.Message, data):
        _, created = await create_user(message.from_user.username, message.from_user.id)
        if created:
            keyboard = types.InlineKeyboardMarkup()
            url = types.InlineKeyboardButton(text='Сайт', url='http://127.0.0.1')
            keyboard.add(url)
            await message.answer(register_message.format(message.from_user.username), reply_markup=keyboard)


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup()
    help_button = types.KeyboardButton(help_label)
    purse_button = types.KeyboardButton(purse_lable)
    keyboard.add(help_button, purse_button)
    await message.answer(start_message, reply_markup=keyboard)


@dp.message_handler(content_types=['text'], regexp="^(\d\d):(\d\d):*")
async def address_by_number_handler(message: types.Message):
    response = await backend.address_by_number(message.text)
    dialog = await new_dialog(message.from_user.id)
    if not response['success']:
        await message.answer(number_not_found_message)
    else:
        await step2_db(dialog, response['data']['number'], response['data']['address'])
        keyboard = types.InlineKeyboardMarkup()
        next_button = types.InlineKeyboardButton(text=next_lable, callback_data='step3')
        keyboard.add(next_button)
        await message.answer(text=step2_message.format(response['data']['address']), reply_markup=keyboard)


def filter_step3(call: types.CallbackQuery):
    return call.data == 'step3'


@dp.callback_query_handler(filter_step3)
async def step3_handler(call: types.CallbackQuery):
    await call.message.delete_reply_markup()
    curent_data = await step3_db(call.from_user.id)
    keyboard = types.InlineKeyboardMarkup()
    variants_line = ''
    for i, service in enumerate(curent_data['services']):
        i += 1
        button = types.InlineKeyboardButton(text=service.button_lable, callback_data=service.id)
        keyboard.row(button)
        variants_line = variants_line + variant_line.format(i=i, name=service.short_name, price=service.price) + '\n'
    await call.message.answer(
        (step3_message.format(**curent_data) + '\n' + variants_line + purse_message.format(**curent_data)),
        reply_markup=keyboard)


async def filter_step4(call: types.CallbackQuery):
    return await get_curent_step(call.from_user.id) == 4


@dp.callback_query_handler(filter_step4)
async def step4_handler(call: types.CallbackQuery):
    await call.message.delete_reply_markup()
    curent_data = await step4_db(call.from_user.id, call.data)
    message = step4_message.format(address=curent_data['address'],
                                   number=curent_data['number'],
                                   service=curent_data['service'].name,
                                   price=curent_data['service'].price)
    purse = purse_message.format(**curent_data)
    keyboard = types.InlineKeyboardMarkup()
    yes = types.InlineKeyboardButton(text=yes_label, callback_data='yes')
    no = types.InlineKeyboardButton(text=no_label, callback_data='no')
    keyboard.add(yes, no)
    await call.message.answer(message + '\n' + purse, reply_markup=keyboard)


@dp.message_handler()
async def address_by_number_handler(message: types.Message):
    await message.answer(help_message)


def main():
    dp.middleware.setup(RegisterUserMiddleware())
    executor.start_polling(dp)


if __name__ == '__main__':
    main()
