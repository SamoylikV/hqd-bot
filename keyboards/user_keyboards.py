from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from state import assortment, user_data, saved_addresses
from utils.delivery_price import get_delivery_price

main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Самовывоз", callback_data="pickup")],
    [InlineKeyboardButton(text="Доставка", callback_data="delivery")]
])

def get_assortment_keyboard(order_type, user_id):
    buttons = []
    for key, product in assortment.items():
        if order_type == "delivery":
            price = product["base_price"] + get_delivery_price(saved_addresses.get(user_id, user_data[user_id]["temp_address"]))
            price = "{:.2f}".format(price)
        else:
            price = product["base_price"]
        text = f"{product['name']} ({price}₽)"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"product_{key}")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_flavor_keyboard(product):
    buttons = []
    for idx, flavor in enumerate(product.get("flavors", [])):
        buttons.append([InlineKeyboardButton(text=flavor, callback_data=f"flavor_{product['name']}_{idx}")])
    buttons.append([InlineKeyboardButton(text="Обратно в меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_price_text_and_keyboard(user_id, product):
    order_type = user_data[user_id]["order_type"]
    if order_type == "pickup":
        final_price = product["final_price"]
        price_text = f"Итоговая цена: {final_price}₽"
        confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить онлайн", callback_data="confirm_order"),
             InlineKeyboardButton(text="Оплатить наличными", callback_data="cash_payment"),
             InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu")
             ]
        ])
    else:
        final_price = product["base_price"]
        price = product["base_price"] + get_delivery_price(saved_addresses[user_id])
        price = "{:.2f}".format(price)
        price_text = f"Итоговая цена: {price}₽ (с доставкой)"
        confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_order"),
             InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_order")]
        ])
    user_data[user_id]["final_price"] = final_price
    return price_text, confirmation_keyboard
