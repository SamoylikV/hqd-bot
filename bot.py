import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ForceReply
)
from config import API_TOKEN, ADMINS_ID

API_TOKEN = API_TOKEN
DELIVERY_FEE = 300

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_data = {}
saved_addresses = {}
active_orders = {}
active_conversations = {}

assortment = {
    "1": {"name": "hqd1", "base_price": 2400, "flavors": ["Клубника", "Банан"]},
    "2": {"name": "hqd2", "base_price": 1500, "flavors": ["Ваниль", "Шоколад"]},
    "3": {"name": "hqd3", "base_price": 2000, "flavors": ["Мята", "Ваниль", "Клубника"]},
}

admin_ids = ADMINS_ID
admin_states = {}

admin_menu_reply = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Редактировать ассортимент")],
        [KeyboardButton(text="Редактировать цену доставки")],
        [KeyboardButton(text="Активные заказы")],
        [KeyboardButton(text="Выйти из админки")]
    ],
    resize_keyboard=True
)

main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="1. Самовывоз", callback_data="pickup")],
    [InlineKeyboardButton(text="2. Доставка", callback_data="delivery")],
    [InlineKeyboardButton(text="3. Настройки", callback_data="settings")]
])


def get_assortment_keyboard(order_type: str):
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


def get_admin_exit_reply_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Выйти из диалога")]], resize_keyboard=True)


async def send_or_edit(chat_id: int, user_id: int, text: str, reply_markup=None):
    last_msg_id = user_data.get(user_id, {}).get("last_message_id")
    if last_msg_id:
        try:
            await bot.edit_message_text(text, chat_id, last_msg_id, reply_markup=reply_markup)
            return last_msg_id
        except Exception:
            try:
                await bot.delete_message(chat_id, last_msg_id)
            except Exception:
                pass
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    user_data.setdefault(user_id, {})["last_message_id"] = msg.message_id
    return msg.message_id


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    user_data.setdefault(user_id, {})
    await send_or_edit(
        message.chat.id, user_id,
        "Добро пожаловать! Выберите опцию:",
        reply_markup=main_menu_keyboard
    )


@dp.message(Command("admin"))
async def admin_handler(message: types.Message):
    user_id = message.from_user.id
    if str(user_id) in admin_ids:
        await send_or_edit(message.chat.id, user_id, "Добро пожаловать в админку!", reply_markup=admin_menu_reply)
    else:
        await send_or_edit(message.chat.id, user_id, "У вас нет доступа в админку.")


@dp.message(lambda m: m.text in ["Редактировать ассортимент", "Редактировать цену доставки", "Активные заказы",
                                 "Выйти из админки"])
async def admin_menu_handler(message: Message):
    user_id = message.from_user.id
    text = message.text

    if text == "Редактировать ассортимент":
        await send_or_edit(message.chat.id, user_id, "Текущий ассортимент:",
                           reply_markup=get_admin_assortment_keyboard())

    elif text == "Редактировать цену доставки":
        await send_or_edit(message.chat.id, user_id, f"Текущая цена доставки: {DELIVERY_FEE}₽\nВведите новую цену:",
                           reply_markup=ForceReply())
        admin_states[user_id] = {"state": "editing_delivery_fee"}

    elif text == "Активные заказы":
        if active_orders:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{order['product']['name']} от {uid}", callback_data=f"active_order_{uid}")]
                for uid, order in active_orders.items()
            ])
            await send_or_edit(message.chat.id, user_id, "Список активных заказов:", reply_markup=kb)
        else:
            await send_or_edit(message.chat.id, user_id, "Нет активных заказов.")

    elif text == "Выйти из админки":
        await send_or_edit(message.chat.id, user_id, "Выход из админки", reply_markup=ReplyKeyboardRemove())
        admin_states.pop(user_id, None)


@dp.message(lambda message: str(message.from_user.id) in admin_ids and message.text == "Выйти из диалога")
async def admin_exit_chat_handler(message: Message):
    user_id = message.from_user.id
    partner_id = active_conversations.get(user_id)
    if partner_id:
        await bot.send_message(partner_id, "Администратор завершил диалог.")
        active_conversations.pop(user_id, None)
        active_conversations.pop(partner_id, None)
        user_data[user_id]["in_chat"] = False
        user_data[partner_id]["in_chat"] = False
        await send_or_edit(message.chat.id, user_id, "Вы вышли из диалога.", reply_markup=admin_menu_reply)
    else:
        await send_or_edit(message.chat.id, user_id, "Вы не в диалоге.")

@dp.message(lambda message: message.text != "Выйти из диалога")
async def handle_messages(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if str(user_id) in admin_ids and user_id in admin_states:
        state_info = admin_states[user_id]
        state = state_info.get("state")
        if "data" not in state_info:
            state_info["data"] = {}

        if state == "adding_product":
            if state_info.get("step") == "name":
                state_info["data"]["name"] = text
                state_info["step"] = "price"
                await send_or_edit(
                    message.chat.id,
                    user_id,
                    "Введите цену продукта:",
                    reply_markup=ForceReply()
                )
                return

            elif state_info.get("step") == "price":
                try:
                    price = int(text)
                    state_info["data"]["price"] = price
                    state_info["step"] = "flavor_input"
                    await send_or_edit(
                        message.chat.id,
                        user_id,
                        "Введите первый вкус продукта (оставьте пустым для завершения):",
                        reply_markup=ForceReply()
                    )
                except ValueError:
                    await send_or_edit(
                        message.chat.id,
                        user_id,
                        "Цена должна быть числом. Введите цену продукта:",
                        reply_markup=ForceReply()
                    )
                return

            elif state_info.get("step") == "flavor_input":
                if text == "":
                    data = state_info["data"]
                    existing_ids = [int(k) for k in assortment.keys() if k.isdigit()]
                    new_id = str(max(existing_ids) + 1) if existing_ids else "1"
                    assortment[new_id] = {
                        "name": data["name"],
                        "base_price": data["price"],
                        "flavors": data.get("flavors", [])
                    }
                    await send_or_edit(
                        message.chat.id,
                        user_id,
                        f"✅ Продукт добавлен:\nID: {new_id}\nНазвание: {data['name']}\n"
                        f"Цена: {data['price']}₽\nВкусы: {', '.join(data['flavors']) or 'нет'}",
                        reply_markup=admin_menu_reply
                    )
                    await message.answer("Обновленный ассортимент:", reply_markup=get_admin_assortment_keyboard())
                    admin_states.pop(user_id, None)
                else:
                    flavor = text.strip()
                    state_info["data"].setdefault("flavors", []).append(flavor)
                    await send_or_edit(
                        message.chat.id,
                        user_id,
                        f"Вкус '{flavor}' добавлен. Хотите добавить еще?",
                        reply_markup=get_flavor_input_keyboard()
                    )
                return

        if state == "editing_product":
            if state_info.get("step") == "name_input":
                new_name = text if text else state_info["data"]["old_name"]
                state_info["data"]["new_name"] = new_name
                state_info["step"] = "price_choice"
                old_price = state_info["data"]["old_price"]
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Изменить цену", callback_data="admin_edit_price_yes"),
                     InlineKeyboardButton(text="Оставить без изменений", callback_data="admin_edit_price_no")]
                ])
                await send_or_edit(
                    message.chat.id,
                    user_id,
                    f"Текущее значение цены: {old_price}₽\nХотите изменить цену?",
                    reply_markup=kb
                )
                return

            elif state_info.get("step") == "price_input":
                try:
                    price = int(text)
                    if price < 100:
                        raise ValueError("Цена не может быть меньше 100₽")
                except ValueError as e:
                    await send_or_edit(
                        message.chat.id,
                        user_id,
                        f"❌ Ошибка: {str(e)}\nВведите цену снова:",
                        reply_markup=ForceReply()
                    )
                    return

                state_info["data"]["new_price"] = price
                prod_id = state_info.get("product_id")
                new_name = state_info["data"].get("new_name", state_info["data"]["old_name"])
                assortment[prod_id].update({"name": new_name, "base_price": price})
                await send_or_edit(
                    message.chat.id,
                    user_id,
                    f"✅ Продукт обновлен!\nID: {prod_id}\nНазвание: {new_name}\nЦена: {price}₽",
                    reply_markup=get_admin_assortment_keyboard()
                )
                admin_states.pop(user_id, None)
                return

        elif state == "editing_product_flavors":
            prod_id = state_info.get("product_id")
            new_flavors = [f.strip() for f in text.split(",") if f.strip()]
            if prod_id in assortment:
                assortment[prod_id]["flavors"] = new_flavors
                await send_or_edit(
                    message.chat.id,
                    user_id,
                    f"Вкусы для продукта {prod_id} обновлены: {', '.join(new_flavors)}",
                    reply_markup=admin_menu_reply
                )
                await send_or_edit(
                    message.chat.id,
                    user_id,
                    "Обновлённый ассортимент:",
                    reply_markup=get_admin_assortment_keyboard()
                )
            else:
                await send_or_edit(
                    message.chat.id,
                    user_id,
                    "Продукт не найден.",
                    reply_markup=admin_menu_reply
                )
            admin_states.pop(user_id, None)
            return

        elif state == "editing_global_flavors":
            new_flavors = [f.strip() for f in text.split(",") if f.strip()]
            await send_or_edit(
                message.chat.id,
                user_id,
                f"Глобальные вкусы обновлены: {', '.join(new_flavors)}",
                reply_markup=admin_menu_reply
            )
            admin_states.pop(user_id, None)
            return

        elif state == "editing_delivery_fee":
            try:
                global DELIVERY_FEE
                DELIVERY_FEE = int(text)
                await send_or_edit(
                    message.chat.id,
                    user_id,
                    f"Цена доставки обновлена: {DELIVERY_FEE}₽",
                    reply_markup=admin_menu_reply
                )
            except ValueError:
                await send_or_edit(
                    message.chat.id,
                    user_id,
                    "Ошибка! Введите целое число:",
                    reply_markup=ForceReply()
                )
                return
            admin_states.pop(user_id, None)
            return
    if user_data.get(user_id, {}).get("in_chat"):
        partner_id = active_conversations.get(user_id)
        if partner_id:
            reply_kb = get_admin_exit_reply_keyboard() if partner_id in admin_ids else None
            await bot.send_message(partner_id, message.text, reply_markup=reply_kb)
        return

    if user_id in admin_ids:
        if text == "Активные заказы":
            if active_orders:
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"{order['product']['name']} от {uid}",
                                          callback_data=f"active_order_{uid}")]
                    for uid, order in active_orders.items()
                ])
                await send_or_edit(message.chat.id, user_id, "Список активных заказов:", reply_markup=kb)
            else:
                await send_or_edit(message.chat.id, user_id, "Нет активных заказов.")
            return

    if user_data.get(user_id, {}).get("awaiting_address", False):
        address = text.strip()
        user_data[user_id]["temp_address"] = address
        user_data[user_id]["awaiting_address"] = False
        save_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="save_address_yes"),
             InlineKeyboardButton(text="Нет", callback_data="save_address_no")]
        ])
        await send_or_edit(
            message.chat.id,
            user_id,
            f"Вы ввели адрес:\n{address}\nЗапомнить адрес для будущих заказов?",
            reply_markup=save_keyboard
        )
        return




@dp.callback_query(lambda c: c.data in ["pickup", "delivery", "settings"])
async def main_menu_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    choice = callback.data
    user_data.setdefault(user_id, {})["order_type"] = choice

    if choice == "pickup":
        await send_or_edit(callback.message.chat.id, user_id, "Вы выбрали самовывоз.\nВот наш ассортимент:",
                           reply_markup=get_assortment_keyboard("pickup"))
    elif choice == "delivery":
        if saved_addresses.get(user_id):
            address = saved_addresses[user_id]
            confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="use_saved_address"),
                 InlineKeyboardButton(text="Нет", callback_data="enter_new_address")]
            ])
            await send_or_edit(callback.message.chat.id, user_id,
                               f"У вас сохранён адрес доставки:\n{address}\nИспользовать его?",
                               reply_markup=confirm_keyboard)
        else:
            await send_or_edit(callback.message.chat.id, user_id, "Пожалуйста, введите адрес доставки:")
            user_data[user_id]["awaiting_address"] = True
            await callback.answer()
            return
    elif choice == "settings":
        await send_or_edit(callback.message.chat.id, user_id, "Настройки пока не реализованы.")
    await callback.answer()


@dp.callback_query(lambda c: c.data in ["use_saved_address", "enter_new_address"])
async def address_choice_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if callback.data == "use_saved_address":
        user_data[user_id]["address"] = saved_addresses[user_id]
        await send_or_edit(callback.message.chat.id, user_id,
                           f"Используем сохранённый адрес:\n{saved_addresses[user_id]}")
        await send_or_edit(callback.message.chat.id, user_id, "Вот наш ассортимент:",
                           reply_markup=get_assortment_keyboard("delivery"))
    else:
        await send_or_edit(callback.message.chat.id, user_id, "Пожалуйста, введите новый адрес доставки:")
        user_data[user_id]["awaiting_address"] = True
    await callback.answer()


@dp.callback_query(lambda c: c.data == "save_address_yes")
async def save_address_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    address = user_data[user_id].get("temp_address")
    if address:
        saved_addresses[user_id] = address
        user_data[user_id]["address"] = address
        await send_or_edit(callback.message.chat.id, user_id, f"Адрес сохранён:\n{address}")
        await send_or_edit(callback.message.chat.id, user_id, "Вот наш ассортимент:",
                           reply_markup=get_assortment_keyboard("delivery"))
    else:
        await send_or_edit(callback.message.chat.id, user_id, "Ошибка: адрес не найден.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "save_address_no")
async def save_address_no_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    address = user_data[user_id].get("temp_address")
    if address:
        user_data[user_id]["address"] = address
        await send_or_edit(callback.message.chat.id, user_id,
                           f"Адрес использован только для текущего заказа:\n{address}")
        await send_or_edit(callback.message.chat.id, user_id, "Вот наш ассортимент:",
                           reply_markup=get_assortment_keyboard("delivery"))
    else:
        await send_or_edit(callback.message.chat.id, user_id, "Ошибка: адрес не найден.")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("product_"))
async def product_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    product_number = callback.data.split("_")[1]
    if product_number not in assortment:
        await send_or_edit(callback.message.chat.id, user_id, "Неверный номер продукта. Попробуйте снова.")
        await callback.answer()
        return
    product = assortment[product_number]
    user_data[user_id]["product"] = product

    if product.get("flavors"):
        await send_or_edit(callback.message.chat.id, user_id, "Выберите вкус:",
                           reply_markup=get_flavor_keyboard(product))
    else:
        price_text, confirmation_keyboard = get_price_text_and_keyboard(user_id, product)
        if user_data[user_id]["order_type"] == "delivery" and not user_data[user_id].get("address"):
            user_data[user_id]["pending_confirmation_text"] = price_text
            user_data[user_id]["pending_confirmation_keyboard"] = confirmation_keyboard
            user_data[user_id]["awaiting_address"] = True
            await send_or_edit(callback.message.chat.id, user_id, "Пожалуйста, введите адрес доставки:")
            await callback.answer()
            return
        await send_or_edit(callback.message.chat.id, user_id, price_text, reply_markup=confirmation_keyboard)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("flavor_") and c.data not in ["flavor_save", "flavor_add_more"])
async def flavor_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data_parts = callback.data.split("_")
    if len(data_parts) < 3:
        await callback.answer("Ошибка выбора вкуса.")
        return
    try:
        flavor_index = int(data_parts[-1])
    except ValueError:
        await callback.answer("Ошибка выбора вкуса.")
        return
    product = user_data[user_id].get("product")
    if not product:
        await callback.answer("Продукт не найден.")
        return
    flavors_list = product.get("flavors", [])
    if flavor_index < 0 or flavor_index >= len(flavors_list):
        await callback.answer("Неверный выбор вкуса.")
        return
    selected_flavor = flavors_list[flavor_index]
    user_data[user_id]["flavor"] = selected_flavor
    price_text, confirmation_keyboard = get_price_text_and_keyboard(user_id, product)
    if user_data[user_id]["order_type"] == "delivery" and not user_data[user_id].get("address"):
        user_data[user_id]["pending_confirmation_text"] = f"Вы выбрали вкус: {selected_flavor}.\n{price_text}"
        user_data[user_id]["pending_confirmation_keyboard"] = confirmation_keyboard
        user_data[user_id]["awaiting_address"] = True
        await send_or_edit(callback.message.chat.id, user_id, "Пожалуйста, введите адрес доставки:")
        await callback.answer()
        return
    await send_or_edit(callback.message.chat.id, user_id, f"Вы выбрали вкус: {selected_flavor}.\n{price_text}",
                       reply_markup=confirmation_keyboard)
    await callback.answer()


@dp.callback_query(lambda c: c.data in ["confirm_order", "cancel_order"])
async def order_confirmation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if callback.data == "confirm_order":
        transfer_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перевод выполнен", callback_data="transfer_done")]
        ])
        await send_or_edit(callback.message.chat.id, user_id,
                           "Пожалуйста, переведите сумму на наш счёт.\nПосле перевода нажмите кнопку для подтверждения.",
                           reply_markup=transfer_keyboard)
    elif callback.data == "cancel_order":
        await send_or_edit(callback.message.chat.id, user_id, "Заказ отменён. Начните заново с команды /start.")
        user_data.pop(user_id, None)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "cash_payment")
async def cash_payment_confirmation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_nick = callback.from_user.username if callback.from_user.username else callback.from_user.first_name
    amount = user_data.get(user_id, {}).get("final_price", "none")
    name = user_data.get(user_id, {}).get("product", {}).get("name", "None")
    flavor = user_data.get(user_id, {}).get("flavor", "none")
    address = user_data.get(user_id, {}).get("address", "none")
    if address == "none":
        address = user_data.get(user_id, {}).get("temp_address", "none")
    msg = await send_or_edit(
        callback.message.chat.id,
        user_id,
        "Ваш оформлен, ожидайте подтверждения администрацией.\nС вами скоро свяжутся",
        reply_markup=None
    )
    user_data[user_id]["payment_message_id"] = msg

    for admin_id in admin_ids:
        print(user_data)
        try:
            if address == "none":
                address = "a"
            callback_data = f"admin_confirm_payment_{user_nick}_{user_id}_{name}_{flavor}_{address}"
            print(callback_data)
            await bot.send_message(
                int(admin_id),
                f"Пользователь @{user_nick} оформил заказ {amount} наличными. Подтвердите заказ",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подтвердить заказ", callback_data=callback_data)]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления администратору {admin_id}: {e}")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "transfer_done")
async def transfer_confirmation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_nick = callback.from_user.username if callback.from_user.username else callback.from_user.first_name
    amount = user_data.get(user_id, {}).get("final_price", "none")
    name = user_data.get(user_id, {}).get("product", {}).get("name", "None")
    flavor = user_data.get(user_id, {}).get("flavor", "none")
    address = user_data.get(user_id, {}).get("address", "none")
    if address == "none":
        address = user_data.get(user_id, {}).get("temp_address", "none")
    msg = await send_or_edit(
        callback.message.chat.id,
        user_id,
        "Ваш платеж подтверждён, ожидайте подтверждения оплаты администрацией.",
        reply_markup=None
    )
    user_data[user_id]["payment_message_id"] = msg

    for admin_id in admin_ids:
        print(admin_id)
        try:
            if address == "none":
                address = "a"
            callback_data = f"admin_confirm_payment_{user_nick}_{user_id}_{name}_{flavor}_{address}"
            print(callback_data)
            await bot.send_message(
                admin_id,
                f"Пользователь @{user_nick} подтвердил перевод на сумму {amount}. Подтвердите, что оплата получена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подтвердить оплату", callback_data=callback_data)]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления администратору {admin_id}: {e}")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("admin_confirm_payment_"))
async def admin_payment_confirmation(callback: types.CallbackQuery):
    customer_id = int(callback.data.split("_")[4])
    payment_msg_id = user_data.get(customer_id, {}).get("payment_message_id")
    product = callback.data.split("_")[5]
    flavor = callback.data.split("_")[6]
    address = callback.data.split("_")[7]
    if payment_msg_id:
        try:
            await bot.edit_message_text(
                "Оплата подтверждена администратором. Ваш заказ оформлен. Спасибо!",
                chat_id=customer_id,
                message_id=payment_msg_id
            )
        except Exception as e:
            logging.error(f"Не удалось обновить сообщение: {e}")
    try:
        if address != "a":
            await callback.message.edit_text(f"Оплата подтверждена.\nДОСТАВКА\n{product}\n{flavor}\n{address}")
        else:
            await callback.message.edit_text(f"Оплата подтверждена.\nСАМОВЫВОЗ\n{product}\n{flavor}")
    except Exception:
        pass
    active_orders[customer_id] = {
        "user_id": customer_id,
        "product": user_data.get(customer_id, {}).get("product"),
        "flavor": user_data.get(customer_id, {}).get("flavor"),
        "order_type": user_data.get(customer_id, {}).get("order_type"),
        "final_price": user_data.get(customer_id, {}).get("final_price"),
        "address": user_data.get(customer_id, {}).get("address")
    }
    await callback.answer("Платеж подтвержден.")


@dp.callback_query(lambda c: c.data == "admin_back_to_menu")
async def admin_back_to_menu(callback: types.CallbackQuery):
    await send_or_edit(callback.message.chat.id, callback.from_user.id,
                       "Возврат в главное меню админки.",
                       reply_markup=admin_menu_reply)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_add_product")
async def admin_add_product(callback: types.CallbackQuery):
    admin_states[callback.from_user.id] = {
        "state": "adding_product",
        "step": "name",
        "data": {"flavors": []}
    }
    await send_or_edit(callback.message.chat.id, callback.from_user.id,
                       "Введите название продукта:",
                       reply_markup=ForceReply())
    await callback.answer()


@dp.callback_query(lambda c: c.data in ["flavor_add_more", "flavor_save"])
async def flavor_input_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in admin_states or admin_states[user_id].get("state") != "adding_product":
        await callback.answer("Нет активного процесса добавления продукта.", show_alert=True)
        return
    if callback.data == "flavor_add_more":
        await send_or_edit(callback.message.chat.id, user_id,
                           "Введите следующий вкус продукта:",
                           reply_markup=ForceReply())
        await callback.answer()
    elif callback.data == "flavor_save":
        data = admin_states[user_id]["data"]
        new_id = str(max([int(k) for k in assortment.keys()] + [0]) + 1)
        assortment[new_id] = {
            "name": data.get("name"),
            "base_price": data.get("price"),
            "flavors": data.get("flavors", [])
        }
        await send_or_edit(callback.message.chat.id, user_id,
                           f"Продукт добавлен: {new_id}. {data.get('name')} ({data.get('price')}₽)\n"
                           f"Вкусы: {', '.join(data.get('flavors', [])) if data.get('flavors') else 'нет'}",
                           reply_markup=admin_menu_reply)
        admin_states.pop(user_id, None)
        await send_or_edit(callback.message.chat.id, user_id,
                           "Обновлённый ассортимент:",
                           reply_markup=get_admin_assortment_keyboard())
        await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("admin_product_"))
async def admin_product_options(callback: types.CallbackQuery):
    product_id = callback.data.split("_")[-1]
    product = assortment.get(product_id)
    if product:
        text = f"Продукт {product_id}: {product['name']} ({product['base_price']}₽)"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Редактировать", callback_data=f"admin_edit_product_{product_id}"),
                InlineKeyboardButton(text="Редактировать вкусы", callback_data=f"admin_edit_flavors_{product_id}")
            ],
            [
                InlineKeyboardButton(text="Удалить", callback_data=f"admin_del_{product_id}")
            ]
        ])
        await send_or_edit(callback.message.chat.id, callback.from_user.id, text, reply_markup=kb)
    else:
        await send_or_edit(callback.message.chat.id, callback.from_user.id, "Продукт не найден.")
    await callback.answer()



@dp.callback_query(lambda c: c.data.startswith("admin_edit_product_"))
async def admin_edit_product(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    product_id = str(callback.data).split("_")[-1]
    print(f"admin_edit_product: product_id из callback: {product_id}")
    print(f"Текущие ключи assortment: {list(assortment.keys())}")

    if str(user_id) not in admin_ids:
        await callback.answer("Доступ запрещен!")
        return
    if product_id not in assortment:
        await callback.answer("Продукт не найден!")
        return
    old_product = assortment[product_id]
    admin_states[user_id] = {
        "state": "editing_product",
        "product_id": product_id,
        "step": "name_choice",
        "data": {
            "old_name": old_product.get("name"),
            "old_price": old_product.get("base_price")
        }
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить название", callback_data="admin_edit_name_yes"),
         InlineKeyboardButton(text="Оставить текущее", callback_data="admin_edit_name_no")]
    ])
    await send_or_edit(
        callback.message.chat.id,
        user_id,
        f"Редактирование продукта {product_id}\nТекущее название: {old_product.get('name')}\nХотите изменить название?",
        reply_markup=kb
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data in ["admin_edit_name_yes", "admin_edit_name_no"])
async def handle_edit_product_name(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in admin_states or admin_states[user_id].get("state") != "editing_product":
        await callback.answer("Нет активного процесса редактирования продукта.", show_alert=True)
        return
    state_info = admin_states[user_id]
    old_name = state_info["data"]["old_name"]
    if callback.data == "admin_edit_name_yes":
        state_info["step"] = "name_input"
        await send_or_edit(
            callback.message.chat.id,
            user_id,
            f"Введите новое название продукта (текущее: {old_name}):",
            reply_markup=ForceReply()
        )
    else:
        state_info["data"]["new_name"] = old_name
        state_info["step"] = "price_choice"
        old_price = state_info["data"]["old_price"]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить цену", callback_data="admin_edit_price_yes"),
             InlineKeyboardButton(text="Оставить без изменений", callback_data="admin_edit_price_no")]
        ])
        await send_or_edit(
            callback.message.chat.id,
            user_id,
            f"Текущая цена: {old_price}₽\nХотите изменить цену?",
            reply_markup=kb
        )
    await callback.answer()


@dp.callback_query(lambda c: c.data in ["admin_edit_price_yes", "admin_edit_price_no"])
async def handle_edit_product_price(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in admin_states or admin_states[user_id].get("state") != "editing_product":
        await callback.answer("Нет активного процесса редактирования продукта.", show_alert=True)
        return
    state_info = admin_states[user_id]
    old_price = state_info["data"]["old_price"]
    if callback.data == "admin_edit_price_yes":
        state_info["step"] = "price_input"
        await send_or_edit(
            callback.message.chat.id,
            user_id,
            f"Введите новую цену продукта (текущая: {old_price}₽):",
            reply_markup=ForceReply()
        )
    else:
        state_info["data"]["new_price"] = old_price
        prod_id = state_info.get("product_id")
        new_name = state_info["data"].get("new_name", state_info["data"]["old_name"])
        new_price = state_info["data"]["new_price"]
        assortment[prod_id].update({"name": new_name, "base_price": new_price})
        await send_or_edit(
            callback.message.chat.id,
            user_id,
            f"✅ Продукт обновлен!\nID: {prod_id}\nНазвание: {new_name}\nЦена: {new_price}₽",
            reply_markup=get_admin_assortment_keyboard()
        )
        admin_states.pop(user_id, None)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("admin_edit_flavors_"))
async def admin_edit_product_flavors(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    product_id = callback.data.split("_")[-1]
    if product_id not in assortment:
        await callback.answer("Продукт не найден!", show_alert=True)
        return
    admin_states[user_id] = {
        "state": "editing_product_flavors",
        "product_id": product_id
    }
    await send_or_edit(callback.message.chat.id, user_id,
                       f"Введите новые вкусы для продукта {product_id} через запятую:",
                       reply_markup=ForceReply())
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("admin_del_"))
async def admin_del_product(callback: types.CallbackQuery):
    product_id = callback.data.split("_")[-1]
    product = assortment.get(product_id)
    if not product:
        await send_or_edit(callback.message.chat.id, callback.from_user.id,
                           "Продукт не найден.",
                           reply_markup=get_admin_assortment_keyboard())
        await callback.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить удаление", callback_data=f"admin_confirm_del_{product_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data="admin_cancel_del")]
    ])
    await send_or_edit(callback.message.chat.id, callback.from_user.id,
                       f"Вы уверены, что хотите удалить продукт {product_id}: {product['name']} ({product['base_price']}₽)?",
                       reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("admin_confirm_del_"))
async def admin_confirm_del(callback: types.CallbackQuery):
    product_id = callback.data.split("_")[-1]
    if product_id in assortment:
        del assortment[product_id]
        await send_or_edit(callback.message.chat.id, callback.from_user.id,
                           f"Продукт {product_id} удалён.")
    else:
        await send_or_edit(callback.message.chat.id, callback.from_user.id,
                           "Продукт не найден.")
    await bot.send_message(callback.from_user.id, "Обновлённый ассортимент:",
                           reply_markup=get_admin_assortment_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_cancel_del")
async def admin_cancel_del(callback: types.CallbackQuery):
    await send_or_edit(callback.message.chat.id, callback.from_user.id,
                       "Операция отменена.",
                       reply_markup=get_admin_assortment_keyboard())
    await callback.answer()


def start_conversation(admin_id: int, customer_id: int):
    active_conversations[customer_id] = admin_id
    active_conversations[admin_id] = customer_id
    user_data.setdefault(customer_id, {})["in_chat"] = True
    user_data.setdefault(admin_id, {})["in_chat"] = True


@dp.callback_query(lambda c: c.data.startswith("active_order_"))
async def active_order_handler(callback: types.CallbackQuery):
    customer_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    start_conversation(admin_id, customer_id)
    await send_or_edit(callback.message.chat.id, admin_id, f"Начался диалог с пользователем {customer_id}.",
                       reply_markup=get_admin_exit_reply_keyboard())
    await bot.send_message(customer_id, "Администратор начал диалог с вами.", reply_markup=None)
    await callback.answer()


@dp.message(
    lambda message: message.from_user.id not in admin_ids and message.from_user.id in user_data and user_data.get(
        message.from_user.id, {}).get("in_chat"))
async def customer_chat_handler(message: Message):
    """
    Обработчик сообщений от заказчика в диалоге.
    Для заказчика не добавляем клавиатуру выхода.
    """
    partner = active_conversations.get(message.from_user.id)
    if partner:
        await bot.send_message(partner, message.text,
                               reply_markup=get_admin_exit_reply_keyboard() if partner in admin_ids else None)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
