import logging
import uuid

from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.user_keyboards import get_assortment_keyboard, get_price_text_and_keyboard, get_flavor_keyboard
from state import user_data, admin_ids, assortment, send_or_edit, saved_addresses, payment_requests

router = Router(name="user_interaction")

@router.callback_query(lambda c: c.data in ["pickup", "delivery", "settings"])
async def main_menu_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    choice = callback.data
    user_data.setdefault(user_id, {})["order_type"] = choice

    if choice == "pickup":
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           "Вы выбрали самовывоз.\nВот наш ассортимент:",
                           reply_markup=get_assortment_keyboard("pickup"))
    elif choice == "delivery":
        if saved_addresses.get(user_id):
            address = saved_addresses[user_id]
            confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="use_saved_address"),
                 InlineKeyboardButton(text="Нет", callback_data="enter_new_address")]
            ])
            await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                               f"У вас сохранён адрес доставки:\n{address}\nИспользовать его?",
                               reply_markup=confirm_keyboard)
        else:
            await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Пожалуйста, введите адрес доставки:")
            user_data[user_id]["awaiting_address"] = True
            await callback.answer()
            return
    elif choice == "settings":
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Настройки пока не реализованы.")
    await callback.answer()


@router.callback_query(lambda c: c.data in ["use_saved_address", "enter_new_address"])
async def address_choice_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if callback.data == "use_saved_address":
        user_data[user_id]["address"] = saved_addresses[user_id]
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           f"Используем сохранённый адрес:\n{saved_addresses[user_id]}")
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Вот наш ассортимент:",
                           reply_markup=get_assortment_keyboard("delivery"))
    else:
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Пожалуйста, введите новый адрес доставки:")
        user_data[user_id]["awaiting_address"] = True
    await callback.answer()


@router.callback_query(lambda c: c.data == "save_address_yes")
async def save_address_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    address = user_data[user_id].get("temp_address")
    if address:
        saved_addresses[user_id] = address
        user_data[user_id]["address"] = address
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, f"Адрес сохранён:\n{address}")
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Вот наш ассортимент:",
                           reply_markup=get_assortment_keyboard("delivery"))
    else:
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Ошибка: адрес не найден.")
    await callback.answer()


@router.callback_query(lambda c: c.data == "save_address_no")
async def save_address_no_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    address = user_data[user_id].get("temp_address")
    if address:
        user_data[user_id]["address"] = address
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           f"Адрес использован только для текущего заказа:\n{address}")
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Вот наш ассортимент:",
                           reply_markup=get_assortment_keyboard("delivery"))
    else:
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Ошибка: адрес не найден.")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("product_"))
async def product_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    product_number = callback.data.split("_")[1]
    if product_number not in assortment:
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           "Неверный номер продукта. Попробуйте снова.")
        await callback.answer()
        return
    product = assortment[product_number]
    user_data[user_id]["product"] = product

    if product.get("flavors"):
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Выберите вкус:",
                           reply_markup=get_flavor_keyboard(product))
    else:
        price_text, confirmation_keyboard = get_price_text_and_keyboard(user_id, product)
        if user_data[user_id]["order_type"] == "delivery" and not user_data[user_id].get("address"):
            user_data[user_id]["pending_confirmation_text"] = price_text
            user_data[user_id]["pending_confirmation_keyboard"] = confirmation_keyboard
            user_data[user_id]["awaiting_address"] = True
            await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Пожалуйста, введите адрес доставки:")
            await callback.answer()
            return
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, price_text,
                           reply_markup=confirmation_keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("flavor_") and c.data not in ["flavor_save", "flavor_add_more"])
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
        await send_or_edit(callback.bot, callback.message.chat.id, user_id, "Пожалуйста, введите адрес доставки:")
        await callback.answer()
        return
    await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                       f"Вы выбрали вкус: {selected_flavor}.\n{price_text}",
                       reply_markup=confirmation_keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data in ["confirm_order", "cancel_order"])
async def order_confirmation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if callback.data == "confirm_order":
        transfer_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перевод выполнен", callback_data="transfer_done")]
        ])
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           "Пожалуйста, переведите сумму на наш счёт.\nПосле перевода нажмите кнопку для подтверждения.",
                           reply_markup=transfer_keyboard)
    elif callback.data == "cancel_order":
        await send_or_edit(callback.bot, callback.message.chat.id, user_id,
                           "Заказ отменён. Начните заново с команды /start.")
        user_data.pop(user_id, None)
    await callback.answer()


@router.callback_query(lambda c: c.data == "cash_payment")
async def cash_payment_confirmation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_nick = callback.from_user.username if callback.from_user.username else callback.from_user.first_name
    user_data_entry = user_data.get(user_id, {})
    request_id = str(uuid.uuid4())
    payment_requests[request_id] = {
        "user_id": user_id,
        "user_nick": callback.from_user.username or callback.from_user.first_name,
        "amount": user_data_entry.get("final_price", "none"),
        "product_name": user_data_entry.get("product", {}).get("name", "None"),
        "flavor": user_data_entry.get("flavor", "none"),
        "address": user_data_entry.get("address") or user_data_entry.get("temp_address", "none")
    }
    amount = user_data_entry.get("final_price", "none")
    msg = await send_or_edit(callback.bot,
                             callback.message.chat.id,
                             user_id,
                             "Ваш оформлен, ожидайте подтверждения администрацией.\nС вами скоро свяжутся",
                             reply_markup=None
                             )
    user_data[user_id]["payment_message_id"] = msg

    for admin_id in admin_ids:
        try:
            await callback.bot.send_message(
                int(admin_id),
                f"Пользователь @{user_nick} оформил заказ {amount} наличными. Подтвердите заказ",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подтвердить заказ", callback_data=f"admin_confirm_payment_{request_id}")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления администратору {admin_id}: {e}")
    await callback.answer()


@router.callback_query(lambda c: c.data == "transfer_done")
async def transfer_confirmation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_nick = callback.from_user.username if callback.from_user.username else callback.from_user.first_name
    user_data_entry = user_data.get(user_id, {})
    request_id = str(uuid.uuid4())
    payment_requests[request_id] = {
        "user_id": user_id,
        "user_nick": callback.from_user.username or callback.from_user.first_name,
        "amount": user_data_entry.get("final_price", "none"),
        "product_name": user_data_entry.get("product", {}).get("name", "None"),
        "flavor": user_data_entry.get("flavor", "none"),
        "address": user_data_entry.get("address") or user_data_entry.get("temp_address", "none")
    }
    amount = user_data_entry.get("final_price", "none")
    msg = await send_or_edit(callback.bot,
                             callback.message.chat.id,
                             user_id,
                             "Ваш платеж подтверждён, ожидайте подтверждения оплаты администрацией.",
                             reply_markup=None
                             )
    user_data[user_id]["payment_message_id"] = msg

    for admin_id in admin_ids:
        try:
            await callback.bot.send_message(
                admin_id,
                f"Пользователь @{user_nick} подтвердил перевод на сумму {amount}. Подтвердите, что оплата получена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Подтвердить оплату", callback_data=f"admin_confirm_payment_{request_id}")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления администратору {admin_id}: {e}")
    await callback.answer()
