import functools
import os
import re
import textwrap

import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext import Filters, Updater

from molti_api_requests import get_all_products, get_access_token, get_product, \
    get_product_main_image_id, download_product_main_image, \
    add_product_to_cart, get_cart_items, remove_item_from_cart, create_customer
from build_menu import built_menu

_database = None


def get_menu(update, context, access_token):
    """
    Хэндлер для состояния MENU.

    Бот демонстрирует пользователю перечень доступных для покупки продуктов и
    переводит его в состояние HANDLE_MENU.

    Теперь в ответ на действия пользователя будет запускаеться хэндлер
    handle_menu.
    """
    products = get_all_products(access_token)['data']
    product_ids = [product['id'] for product in products]
    product_names = [product['attributes']['name'] for product in products]
    product_ids_and_names = dict(zip(product_ids, product_names))

    buttons = [
        InlineKeyboardButton(
            product_name, callback_data=product_id) for
        product_id, product_name in product_ids_and_names.items()
    ]

    reply_markup = InlineKeyboardMarkup(built_menu(
        buttons=buttons,
        n_cols=2,
        footer_buttons=[InlineKeyboardButton('Корзина', callback_data='cart')])
    )
    message_text = '\nКакой товар вас интересует?'

    context.bot.send_message(
        text=message_text,
        chat_id=update.effective_chat.id,
        reply_markup=reply_markup,
    )
    return "HANDLE_MENU"


def handle_menu(update, context, access_token):
    """
    Хэндлер для состояния HANDLE_MENU.

    Если пользователь выбрал товар, то бот отправляет фото и описание
    выбранного товара и переводит его в состояние HANDLE_DESCRIPTION.

    Если пользователь нажал кнопку "Корзина", то отправляет ему описание
    содержимого корзины и переводит его в состояние HANDLE_CART.
    """
    if update.callback_query.data != 'cart':
        product_id = update.callback_query.data
        main_image_id = get_product_main_image_id(access_token, product_id)
        main_image_path = download_product_main_image(access_token,
                                                      main_image_id)

        with open(main_image_path, 'rb') as image:
            main_image = image.read()

        product = get_product(access_token, product_id)['data']
        product_name = product['attributes']['name']
        description = product['attributes']['description']
        price = product['meta']['display_price']['without_tax']['formatted']

        keyboard = [
            [
                InlineKeyboardButton('1 упаковка',
                                     callback_data=f'{product_id}_1'),
                InlineKeyboardButton('3 упаковки',
                                     callback_data=f'{product_id}_3'),
                InlineKeyboardButton('5 упаковок',
                                     callback_data=f'{product_id}_5')
            ],
            [InlineKeyboardButton('Корзина', callback_data='cart')],
            [InlineKeyboardButton('В меню', callback_data='menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=main_image,
            caption=f'{product_name}\n\n{description}\n\n{price}',
            reply_markup=reply_markup,
        )

        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
        )
        return "HANDLE_DESCRIPTION"
    else:
        message_text = ''
        buttons = []
        cart_id = update.callback_query.from_user.id
        response = get_cart_items(access_token, cart_id)
        products = response['data']
        total_price = response['meta']['display_price']['without_tax']['formatted']
        for product in products:
            product_name = product["name"]
            cart_item_id = product["id"]
            description = product["description"]
            price = product["meta"]["display_price"]["without_tax"]["unit"]["formatted"]
            quantity = product["quantity"]
            product_sum = product["meta"]["display_price"]["without_tax"]["value"]["formatted"]
            message_text += textwrap.dedent(f'''
                            {product_name}
                            {description}
                            {price} за упаковку
                            {quantity} упаковок в корзине на сумму {product_sum}
                            
                            ''')

            buttons.append(InlineKeyboardButton(f'Убрать из корзины {product_name}',
                                                callback_data=cart_item_id))

        reply_markup = InlineKeyboardMarkup(built_menu(
            buttons=buttons,
            n_cols=1,
            footer_buttons=[InlineKeyboardButton('В меню', callback_data='menu'),
                            InlineKeyboardButton('Оплата', callback_data='payment')])
        )

        message_text = f'{message_text}Итого: {total_price}'
        context.bot.send_message(
            text=message_text,
            chat_id=update.effective_chat.id,
            reply_markup=reply_markup,
        )
        return "HANDLE_CART"


def handle_description(update, context, access_token):
    """
    Хэндлер для состояния HANDLE_DESCRIPTION.

    Если пользователь выбрал один из вариантов кол-ва товара, то добавляет
    товар в указанном кол-ве в корзину и оставляет его в состоянии
    HANDLE_DESCRIPTION.

    Если пользователь нажал кнопку "Корзина", то отправляет ему описание
    содержимого корзины и переводит его в состояние HANDLE_CART.

    Если пользователь нажал кнопку "Меню", то бот выводит на экран
    исходный перечень продуктов и переводит его в состояние HANDLE_MENU.

    """
    if update.callback_query.data == 'menu':
        return get_menu(update, context, access_token)
    elif update.callback_query.data == 'cart':
        return handle_menu(update, context, access_token)
    else:
        user_id = update.callback_query.from_user.id
        product_id, quantity = update.callback_query.data.split('_')
        quantity = int(quantity)

        add_product_to_cart(
            access_token,
            product_id=product_id,
            quantity=quantity,
            card_id=user_id,
        )
        return "HANDLE_DESCRIPTION"


def handle_cart(update, context, access_token):
    """
    Хэндлер для состояния HANDLE_CART.

    Удаляет товар из корзины при нажатии на кнопку "Удалить <название товара>".

    Если пользователь нажал кнопку "Меню", то бот выводит на экран
    исходный перечень продуктов и переводит его в состояние HANDLE_MENU.

    Если пользователь нажал кнопку "Оплата", то бот запросит почту пользователя
    и переводит его в состояние WAITING_EMAIL.
    """
    if update.callback_query.data == 'menu':
        return get_menu(update, context, access_token)
    elif update.callback_query.data == 'payment':
        text = 'Напишите, пожалуйста, вашу электронную почту'
        context.bot.send_message(
            text=text,
            chat_id=update.effective_chat.id,
        )
        return "WAITING_EMAIL"
    else:
        remove_item_from_cart(
            access_token,
            cart_id=update.callback_query.from_user.id,
            cart_item_id=update.callback_query.data,
        )
        return "HANDLE_CART"


def handle_waiting_email(update, context, access_token):
    """
        Хэндлер для состояния WAITING_EMAIL.

        Как только пользователь введёт свою почту, бот создаст клиента в CMS
    """
    email_pattern = r'[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+$'
    user_reply = update.message.text
    if re.fullmatch(email_pattern, user_reply):
        update.message.reply_text(f'Ваша почта: {user_reply}')
        create_customer(
            access_token,
            email=user_reply,
        )
    else:
        error_text = 'Введена некорректная почта. Попробуйте ещё раз.'
        update.message.reply_text(error_text)
        return "WAITING_EMAIL"


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
        user_state = 'MENU'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'MENU': get_menu,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': handle_waiting_email,
    }

    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context, access_token)
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
