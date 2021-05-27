import os
from loguru import logger

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.middlewares import BaseMiddleware

from rr_backend.backend import Backend
from rr_telebot.database_handler import create_user, new_dialog, get_curent_step, get_price_list, save_dialog, \
    get_dialog, create_order, save_dadata_varinants, pick_address, save_data_to_dialog
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
    logger.debug('start')
    # keyboard = types.ReplyKeyboardMarkup()
    # help_button = types.KeyboardButton(help_label)
    # purse_button = types.KeyboardButton(purse_lable)
    # keyboard.add(help_button, purse_button)
    keyboard = types.InlineKeyboardMarkup()
    join_button = types.InlineKeyboardButton(text=join_lable, callback_data='join')
    keyboard.add(join_button)
    await message.answer(start_message, reply_markup=keyboard)


def join_filter(call: types.CallbackQuery):
    return call.data == 'join'


@dp.callback_query_handler(join_filter)
async def join_handler(call: types.CallbackQuery):
    await call.message.delete()
    keyboard = types.ReplyKeyboardMarkup()
    help_button = types.KeyboardButton(help_label)
    gift_button = types.KeyboardButton(gift_label)
    account_button = types.KeyboardButton(account_label)
    purse_button = types.KeyboardButton(purse_lable)
    keyboard.add(help_button, account_button)
    keyboard.add(gift_button, purse_button)
    await call.message.answer(messagr_after_join, reply_markup=keyboard)


@dp.message_handler(content_types=['text'], regexp=gift_label)
async def gift_handler(message: types.Message):
    await message.answer('not implemented')


@dp.message_handler(content_types=['text'], regexp=account_label)
async def account_handler(message: types.Message):
    await message.answer('not implemented')


@dp.message_handler(content_types=['text'], regexp=purse_lable)
async def purse_handler(message: types.Message):
    await message.answer('not implemented')


@dp.message_handler(content_types=['text'], regexp=".* .* .*")
async def address_handler(message: types.Message):
    dadata = await Backend.async_find_adress(message.text)
    if len(dadata) == 0:
        await message.answer(address_not_found)
    # elif len(dadata) >= 4:
    #     await message.answer(too_many_addresses)
    else:
        await save_dadata_varinants(message.from_user.id, dadata)
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text=next_lable, callback_data='0')
        keyboard.row(button)
        await message.answer(dadata[0]['value'], reply_markup=keyboard)


async def filter_step1(call: types.CallbackQuery):
    return await get_curent_step(call.from_user.id) == 1


@dp.callback_query_handler(filter_step1)
async def pick_address_handler(call: types.CallbackQuery):
    await call.message.delete()
    dialog = await pick_address(call.from_user.id, int(call.data))
    results = await Backend.async_objects_by_address(dialog.dadata)
    await save_data_to_dialog(call.from_user.id, results)
    logger.debug(results)
    text = str()
    buttons = []
    for i, result in enumerate(results):
        logger.debug(result)
        text += f'\nОбъект {i + 1}:'
        buttons.append(types.InlineKeyboardButton(text=f'Объект {i + 1}', callback_data=i))
        text += f"\n{result['EGRN']['object']['CADNOMER']} - {result['EGRN']['object']['ADDRESS']}"
        text += f"\nСтатус объекта: {result['EGRN']['details']['Статус объекта']}\n" or 'Неизвестно\n'

    keyboard = types.InlineKeyboardMarkup()
    for button in buttons:
        keyboard.add(button)
    await call.message.answer(text, reply_markup=keyboard)


async def print_full_info(message: types.Message, dialog, result):
    text = str()
    for key, value in result['EGRN']['details'].items():
        text += f'\n{key}: {value}'
    price_list = await get_price_list()
    keyboard = types.InlineKeyboardMarkup()
    for price in price_list:
        button = types.InlineKeyboardButton(text=f'{price["short_name"]} за {price["price"]}',
                                            callback_data=price['id'])
        keyboard.add(button)
    dialog.step = 3
    await save_dialog(dialog)
    await message.answer(text, reply_markup=keyboard)


async def filter_step2(call: types.CallbackQuery):
    return await get_curent_step(call.from_user.id) == 2


@dp.callback_query_handler(filter_step2)
async def object_info_handler(call: types.CallbackQuery):
    await call.message.delete()
    dialog = await get_dialog(call.from_user.id)
    result = dialog.data[int(call.data)]
    await print_full_info(call.message, dialog, result)


@dp.message_handler(content_types=['text'], regexp="^(\d\d):(\d\d):*")
async def address_by_number_handler(message: types.Message):
    dialog = await new_dialog(message.from_user.id)
    result = await Backend.async_object_by_number(message.text)
    dialog.data = result
    await print_full_info(message, dialog, result)


@dp.message_handler(content_types=['text'])
async def any_message_handler(message: types.Message):
    logger.debug(message.text)
    await message.answer(help_message)


def main():
    dp.middleware.setup(RegisterUserMiddleware())
    executor.start_polling(dp)


if __name__ == '__main__':
    main()
