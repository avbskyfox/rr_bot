import os
from loguru import logger

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.middlewares import BaseMiddleware

from rr_backend.backend import Backend
from rr_backend.t_backend import async_backend as t_backend
from rr_telebot.database_handler import create_user, new_dialog, get_curent_step, step4_db, \
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
        text += f'\nОбъект {i+1}:'
        buttons.append(types.InlineKeyboardButton(text=f'Объект {i+1}', callback_data=i))
        # for key, value in result['EGRN']['details'].items():
        #     text += f'\n{key}: {value}'
        text += f"\n{result['EGRN']['object']['CADNOMER']} - {result['EGRN']['object']['ADDRESS']}"
        text += f"\nСтатус объекта: {result['EGRN']['details']['Статус объекта']}\n" or 'Неизвестно\n'

    keyboard = types.InlineKeyboardMarkup()
    for button in buttons:
        keyboard.add(button)
    await call.message.answer(text, reply_markup=keyboard)


async def filter_step2(call: types.CallbackQuery):
    return await get_curent_step(call.from_user.id) == 2


@dp.callback_query_handler(filter_step2)
async def object_info_handler(call: types.CallbackQuery):
    await call.message.delete()
    dialog = await get_dialog(call.from_user.id)
    result = dialog.data[int(call.data)]
    text = str()
    for key, value in result['EGRN']['details'].items():
        text += f'\n{key}: {value}'
    await call.message.answer(text)


@dp.message_handler(content_types=['text'], regexp="^(\d\d):(\d\d):*")
async def address_by_number_handler(message: types.Message):
    response = await t_backend.address_by_number(message.text)
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
        variants_line = variants_line + variant_line.format(i=i, name=service.short_name,
                                                            price=service.base_price) + '\n'
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
                                   price=curent_data['service'].base_price)
    purse = purse_message.format(**curent_data)
    keyboard = types.InlineKeyboardMarkup()
    yes = types.InlineKeyboardButton(text=yes_label, callback_data='yes')
    no = types.InlineKeyboardButton(text=no_label, callback_data='no')
    keyboard.add(yes, no)
    await call.message.answer(message + '\n' + purse, reply_markup=keyboard)


async def filter_step5(call: types.CallbackQuery):
    return await get_curent_step(call.from_user.id) == 5


@dp.callback_query_handler(filter_step5)
async def step5_handler(call: types.CallbackQuery):
    await call.message.delete_reply_markup()
    dialog = await get_dialog(call.from_user.id)
    if call.data == 'yes':
        if not dialog['check_ammount']:
            keyboard = types.InlineKeyboardMarkup()
            url = types.InlineKeyboardButton(text='Пополнить', url='http://127.0.0.1')
            next_button = types.InlineKeyboardButton(text=next_lable, callback_data='yes')
            keyboard.add(url, next_button)
            await call.message.answer(not_anought_message.format(**dialog), reply_markup=keyboard)
        else:
            created, order = await create_order(call.from_user.id)
            if created:
                await call.message.answer(order_created_message.format(number=order.number))
            else:
                await call.message.answer(order_not_created_message)
    else:
        await new_dialog(call.from_user.id)


@dp.message_handler(content_types=['text'])
async def any_message_handler(message: types.Message):
    logger.debug(message.text)
    await message.answer(help_message)


def main():
    dp.middleware.setup(RegisterUserMiddleware())
    executor.start_polling(dp)


if __name__ == '__main__':
    main()
