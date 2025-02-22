from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DELIVERY_FEE
from state import assortment, user_data

main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="1. Самовывоз", callback_data="pickup")],
    [InlineKeyboardButton(text="2. Доставка", callback_data="delivery")],
    [InlineKeyboardButton(text="3. Настройки", callback_data="settings")]
])

def get_assortment_keyboard(order_type):
    buttons = []
    for key, product in assortment.items():
        price = product["base_price"] + DELIVERY_FEE if order_type == "delivery" else product["base_price"]
        text = f"{key}. {product['name']} ({price}₽)"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"product_{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_flavor_keyboard(product):
    buttons = []
    for idx, flavor in enumerate(product.get("flavors", [])):
        buttons.append([InlineKeyboardButton(text=flavor, callback_data=f"flavor_{product['name']}_{idx}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_price_text_and_keyboard(user_id, product):
    order_type = user_data[user_id]["order_type"]
    if order_type == "pickup":
        final_price = product["base_price"] - DELIVERY_FEE
        price_text = f"Итоговая цена: {final_price}₽ (самовывоз)"
        confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить онлайн", callback_data="confirm_order"),
             InlineKeyboardButton(text="Оплатить наличными", callback_data="cash_payment")]
        ])
    else:
        final_price = product["base_price"]
        price_text = f"Итоговая цена: {final_price}₽ (с доставкой)"
        confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_order"),
             InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
        ])
    user_data[user_id]["final_price"] = final_price
    return price_text, confirmation_keyboard