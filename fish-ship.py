"""
Работает с этими модулями:
"""
import functools
import os

import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext import Filters, Updater

from molti_api_requests import get_all_products, get_access_token, get_product, \
    get_product_main_image_id, download_product_main_image
from utils import built_product_list

_database = None


def start(update, context, access_token):
    products = get_all_products(access_token)['data']
    product_ids = [product['id'] for product in products]
    product_names = [product['attributes']['name'] for product in products]
    product_ids_and_names = dict(zip(product_ids, product_names))

    keyboard = [
        InlineKeyboardButton(
            product_name, callback_data=product_id) for
        product_id, product_name in product_ids_and_names.items()
    ]

    reply_markup = InlineKeyboardMarkup(built_product_list(keyboard, 2))
    message_text = '\nКакой товар вас интересует?'

    context.bot.send_message(
        text=message_text,
        chat_id=update.effective_chat.id,
        reply_markup=reply_markup,
    )
    return "HANDLE_MENU"


def handle_menu(update, context, access_token):
    product_id = update.callback_query.data
    main_image_id = get_product_main_image_id(access_token, product_id)
    main_image_path = download_product_main_image(access_token, main_image_id)

    with open(main_image_path, 'rb') as image:
        main_image = image.read()

    product = get_product(access_token, product_id)['data']
    product_name = product['attributes']['name']
    description = product['attributes']['description']
    price = product['meta']['display_price']['without_tax']['formatted']

    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id,
    )

    keyboard = [[InlineKeyboardButton('Назад', callback_data='назад')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=main_image,
        caption=f'{product_name}\n\n{description}\n\n{price}',
        reply_markup=reply_markup,
    )
    return "HANDLE_DESCRIPTION"


def handle_description(update, context, access_token):
    if update.callback_query.data == 'назад':
        return start(update, context, access_token)


def handle_users_reply(update, context, access_token):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
    }

    state_handler = states_functions[user_state]
    if user_state in ('START', 'HANDLE_MENU', 'HANDLE_DESCRIPTION'):
        try:
            next_state = state_handler(update, context, access_token)
            db.set(chat_id, next_state)
        except Exception as err:
            print(err)
    else:
        try:
            next_state = state_handler(update, context)
            db.set(chat_id, next_state)
        except Exception as err:
            print(err)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = os.getenv("DATABASE_PASSWORD")
        database_host = os.getenv("DATABASE_HOST")
        database_port = os.getenv("DATABASE_PORT")
        _database = redis.Redis(host=database_host, port=database_port,
                                password=database_password)
    return _database


def main():
    load_dotenv()
    fish_shop_tg_token = os.getenv('FISH_SHOP_TG_TOKEN')
    moltin_client_id = os.getenv('MOLTIN_CLIENT_ID')
    client_secret = os.getenv('MOLTIN_CLIENT_SECRET')
    access_token = get_access_token(moltin_client_id, client_secret)
    handle_users_reply_partial = functools.partial(handle_users_reply,
                                                   access_token=access_token)

    updater = Updater(fish_shop_tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_partial))
    dispatcher.add_handler(MessageHandler(Filters.text,
                                          handle_users_reply_partial))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply_partial))
    updater.start_polling()


if __name__ == '__main__':
    main()
