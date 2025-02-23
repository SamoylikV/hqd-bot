import logging
import uuid
from itertools import product

from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from handlers.chat_handlers import start_conversation
from keyboards.admin_keyboards import admin_menu_reply, get_admin_exit_reply_keyboard, get_order_action_reply_keyboard
from keyboards.user_keyboards import main_menu_keyboard
from state import user_data, active_orders, payment_requests
from utils.send_or_edit import send_or_edit

router = Router(name="admin_orders")


@router.callback_query(lambda c: c.data.startswith("admin_confirm_payment_"))
async def admin_payment_confirmation(callback: types.CallbackQuery):
    request_id = callback.data.split("_")[-1]
    request_data = payment_requests.get(request_id)
    if not request_data:
        await callback.answer("Запрос устарел или не найден!")
        return

    customer_id = request_data["user_id"]
    payment_msg_id = user_data.get(customer_id, {}).get("payment_message_id")
    product = request_data["product_name"]
    flavor = request_data["flavor"]
    address = request_data["address"]
    if payment_msg_id:
        try:
            await callback.bot.edit_message_text(
                "Оплата подтверждена администратором. Ваш заказ оформлен. Спасибо!",
                chat_id=customer_id,
                message_id=payment_msg_id
            )
            await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id, "Добро пожаловать! Выберите опцию:", main_menu_keyboard)
        except Exception as e:
            logging.error(f"Не удалось обновить сообщение: {e}")
    try:
        if address != "none":
            await callback.message.edit_text(f"Оплата подтверждена.\nДОСТАВКА\n{product}\n{flavor}\n{address}")
        else:
            await callback.message.edit_text(f"Оплата подтверждена.\nСАМОВЫВОЗ\n{product}\n{flavor}")
    except Exception:
        pass

    order_id = str(uuid.uuid4())
    active_orders[order_id] = {
        "order_id": order_id,
        "user_id": customer_id,
        "product": user_data.get(customer_id, {}).get("product"),
        "flavor": user_data.get(customer_id, {}).get("flavor"),
        "order_type": user_data.get(customer_id, {}).get("order_type"),
        "final_price": user_data.get(customer_id, {}).get("final_price"),
        "address": user_data.get(customer_id, {}).get("address")
    }
    await callback.answer("Платеж подтвержден.")


@router.callback_query(lambda c: c.data == "admin_back_to_menu")
async def admin_back_to_menu(callback: types.CallbackQuery):
    await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id,
                       "Возврат в главное меню админки.",
                       reply_markup=admin_menu_reply)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("active_order_"))
async def active_order_handler(callback: types.CallbackQuery):
    customer_id = int(callback.data.split("_")[-1])
    order_id_suffix = callback.data.split("_")[-2]
    admin_id = callback.from_user.id
    full_order_id = next((key for key in active_orders if key.endswith(order_id_suffix)), None)

    order = active_orders.get(full_order_id, {})
    product_name = order.get("product", {}).get("name", "")
    flavor = order.get("flavor", "")
    order_type = "Самовывоз" if order.get("order_type", "") == "pickup" else "Доставка"
    address = order.get("address", "") or ""
    price = order.get("final_price", "")

    html_message = (
        f"<b>Заказ от клиента:</b> <code>{customer_id}</code><br>"
        f"<b>Тип заказа:</b> {order_type}<br>"
        f"<b>Продукт:</b> {product_name}<br>"
        f"<b>Вкус:</b> {flavor}<br>"
        f"<b>Адрес:</b> {address}<br>"
        f"<b>Цена:</b> {price}"
    )

    await send_or_edit(
        callback.bot,
        callback.message.chat.id,
        admin_id,
        html_message,
        parse_mode="HTML",
        reply_markup=get_order_action_reply_keyboard(customer_id, order_id_suffix)
    )

@router.callback_query(lambda c: c.data.startswith("start_chat_"))
async def start_chat(callback: types.CallbackQuery):
    customer_id = int(callback.data.split("_")[-1])
    admin_id = callback.from_user.id
    start_conversation(admin_id, customer_id)
    await send_or_edit(callback.bot, callback.message.chat.id, admin_id,
                       f"Начался диалог с пользователем {customer_id}.",
                       reply_markup=get_admin_exit_reply_keyboard())
    await callback.bot.send_message(customer_id, "Администратор начал диалог с вами.", reply_markup=None)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("close_order_"))
async def close_order(callback: types.CallbackQuery):
    order_id_suffix = callback.data.split("_")[-2]

    full_order_id = next((key for key in active_orders if key.endswith(order_id_suffix)), None)
    buttons = [[InlineKeyboardButton(text="Назад", callback_data="admin_back_to_menu")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if full_order_id:
        active_orders.pop(full_order_id)
        await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id, f"Заказ {full_order_id} удален", reply_markup=kb)
    else:
        await send_or_edit(callback.bot, callback.message.chat.id, callback.from_user.id,
                           f"Заказ с окончанием ID {order_id_suffix} не найден.", reply_markup=kb)

    await callback.answer()
