import logging
import uuid
from pickletools import pybytes_or_str

from aiogram import Router, types
from handlers.chat_handlers import start_conversation
from keyboards.admin_keyboards import admin_menu_reply, get_admin_exit_reply_keyboard
from state import user_data, active_orders, send_or_edit, payment_requests

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
    admin_id = callback.from_user.id
    start_conversation(admin_id, customer_id)
    await send_or_edit(callback.bot, callback.message.chat.id, admin_id, f"Начался диалог с пользователем {customer_id}.",
                       reply_markup=get_admin_exit_reply_keyboard())
    await callback.bot.send_message(customer_id, "Администратор начал диалог с вами.", reply_markup=None)
    await callback.answer()