from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from django.conf import settings
from loguru import logger


from rr_backend.backend import Backend
from rr_telebot import database_handler
from rr_telebot.database_handler import create_user, new_dialog, get_curent_step, get_price_list, save_dialog, \
    get_dialog, create_order, save_dadata_varinants, pick_address, save_data_to_dialog
from rr_telebot.template_message import *


bot = Bot(token=settings.TELEGRAM_API_TOKEN)
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
    keyboard = types.InlineKeyboardMarkup()
    join_button = types.InlineKeyboardButton(text=join_lable, callback_data='join')
    keyboard.add(join_button)
    await message.answer(start_message, reply_markup=keyboard)


def join_filter(call: types.CallbackQuery):
    return call.data == 'join'


@dp.callback_query_handler(join_filter)
async def join_handler(call: types.CallbackQuery):
    await call.message.delete()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    help_button = types.KeyboardButton(help_label)
    gift_button = types.KeyboardButton(gift_label)
    account_button = types.KeyboardButton(account_label)
    purse_button = types.KeyboardButton(purse_lable)
    keyboard.add(help_button, account_button)
    keyboard.add(gift_button, purse_button)
    await call.message.answer(messagr_after_join, reply_markup=keyboard)


@dp.message_handler(content_types=['text'], regexp=".* .* .*")
async def address_handler(message: types.Message):
    dadata = await Backend.async_find_adress(message.text)
    if len(dadata) == 0:
        await message.answer(address_not_found)
    else:
        await save_dadata_varinants(message.from_user.id, dadata)
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text=next_lable, callback_data='0')
        keyboard.row(button)
        await message.answer(dadata[0]['value'], reply_markup=keyboard)


async def filter_step1(call: types.CallbackQuery):
    return await get_curent_step(call.from_user.id) == 1


async def filter_equal_zero(call: types.CallbackQuery):
    return call.data == "0"


@dp.callback_query_handler(filter_step1, filter_equal_zero)
async def pick_address_handler(call: types.CallbackQuery):
    await call.message.delete()
    dialog = await pick_address(call.from_user.id, int(call.data))
    results = await Backend.async_objects_by_address(dialog.dadata)
    await save_data_to_dialog(call.from_user.id, results)
    text = str()
    buttons = []
    for i, result in enumerate(results):
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
    dialog.address = result['EGRN']['object']['ADDRESS']
    dialog.number = result['EGRN']['object']['CADNOMER']
    dialog.data = result
    await save_dialog(dialog)
    await print_full_info(call.message, dialog, result)


@dp.message_handler(content_types=['text'], regexp=r"^(\d\d):(\d\d):*")
async def address_by_number_handler(message: types.Message):
    process_message = await message.answer('trying to find...')
    dialog = await new_dialog(message.from_user.id)
    result = await Backend.async_object_by_number(message.text)
    dialog.data = result
    await process_message.delete()
    await print_full_info(message, dialog, result)


async def filter_step3(call: types.CallbackQuery):
    return await get_curent_step(call.from_user.id) == 3


@dp.callback_query_handler(filter_step3)
async def pick_serice(call: types.CallbackQuery):
    await call.message.delete()
    process_message = await call.message.answer('Check your money...')
    money_enoght, dialog = await database_handler.pick_service(call.from_user.id, int(call.data))
    await process_message.delete()
    if money_enoght:
        dialog.step = 4
        await save_dialog(dialog)
        keyboard = types.InlineKeyboardMarkup()
        next_button = types.InlineKeyboardButton(next_lable, callback_data='confirm')
        keyboard.add(next_button)
        await call.message.answer(
            f'adress: {dialog.address}\nservice:{dialog.service.name}\nprice{dialog.service.base_price}',
            reply_markup=keyboard
        )
    else:
        await call.message.answer('Not enoght money')


async def filter_step4(call: types.CallbackQuery):
    return await get_curent_step(call.from_user.id) == 4


@dp.callback_query_handler(filter_step4)
async def create_order_handler(call: types.CallbackQuery):
    if call.data == 'confirm':
        await call.message.delete()
        created, order = await create_order(call.from_user.id)
        if created:
            await call.message.answer('order created')
        else:
            logger.error(order)
            await call.message.answer('can not create order')
        await database_handler.new_dialog(call.from_user.id)


@dp.callback_query_handler()
async def top_up_balance_handler(call: types.CallbackQuery):
    await call.message.delete_reply_markup()
    result = await database_handler.BalanceDialog.async_callback_resolv(call)
    logger.debug(result)
    if not isinstance(result, list):
        result = [result]
    for item in result:
        text, markup = item
        if markup is not None:
            await call.message.answer(text, reply_markup=markup, parse_mode='HTML')
        elif text is not None:
            await call.message.answer(text)


@dp.message_handler()
async def take_amount_handler(message: types.Message):
    result = await database_handler.BalanceDialog.async_message_resolv(message)
    if not isinstance(result, list):
        result = [result]
    for item in result:
        text, markup = item
        logger.debug(text, markup)
        if markup is not None:
            await message.answer(text, reply_markup=markup, parse_mode='HTML')
        elif text is not None:
            await message.answer(text)


def start(loglevel='INFO'):
    logger.add('bot.log', level=loglevel)
    dp.middleware.setup(RegisterUserMiddleware())
    executor.start_polling(dp)


if __name__ == '__main__':
    start('DEBUG')
