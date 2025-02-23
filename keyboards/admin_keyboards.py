from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from state import assortment

admin_menu_reply = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Редактировать ассортимент")],
        [KeyboardButton(text="Редактировать цену доставки")],
        [KeyboardButton(text="Активные заказы")],
        [KeyboardButton(text="Выйти из админки")]
    ],
    resize_keyboard=True
)

def get_admin_assortment_keyboard():
    buttons = []
    for key, prod in assortment.items():
        buttons.append([InlineKeyboardButton(
            text=f"{key}. {prod['name']} ({prod['base_price']}₽)",
            callback_data=f"admin_product_{key}"
        )])
    buttons.append([InlineKeyboardButton(text="Добавить продукт", callback_data="admin_add_product")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_flavor_input_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить еще", callback_data="flavor_add_more"),
         InlineKeyboardButton(text="Сохранить", callback_data="flavor_save")]
    ])

def get_order_action_reply_keyboard(customer_id, order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать чат", callback_data=f"start_chat_{customer_id}"),
         InlineKeyboardButton(text="Закрыть заказ", callback_data=f"close_order_{order_id}_{customer_id}")]
    ])

def get_admin_exit_reply_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Выйти из диалога")]], resize_keyboard=True)