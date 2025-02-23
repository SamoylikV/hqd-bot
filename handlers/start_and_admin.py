from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from config import DELIVERY_FEE
from utils.filters import UserNotInConversation, AdminNotInConversation, AdminNotInMenu
from keyboards.admin_keyboards import get_admin_assortment_keyboard, admin_menu_reply
from keyboards.user_keyboards import main_menu_keyboard

from state import user_data, admin_ids, admin_states, active_orders, active_conversations, send_or_edit, active_admins

router = Router(name="start_and_admin")


@router.message(Command("start"), UserNotInConversation(), AdminNotInMenu())
async def start(message: types.Message):
    user_id = message.from_user.id
    user_data.setdefault(user_id, {})
    await send_or_edit(message.bot,
        message.chat.id, user_id,
        "Добро пожаловать! Выберите опцию:",
        reply_markup=main_menu_keyboard
    )

@router.message(Command("admin"), AdminNotInConversation())
async def admin_handler(message: types.Message):
    user_id = message.from_user.id
    if str(user_id) in admin_ids:
        await send_or_edit(message.bot, message.chat.id, user_id, "Добро пожаловать в админку!", reply_markup=admin_menu_reply)
        active_admins[user_id] = True
    else:
        await send_or_edit(message.bot, message.chat.id, user_id, "У вас нет доступа в админку.")

@router.message(Command("start", "admin"))
async def block_commands_in_conversation(message: Message):
    await message.answer("⚠️ Эта команда сейчас недоступна ⚠️")

@router.message(lambda m: m.text in ["Редактировать ассортимент", "Редактировать цену доставки", "Активные заказы",
                                     "Выйти из админки"])
async def admin_menu_handler(message: Message):
    user_id = message.from_user.id
    text = message.text

    if text == "Редактировать ассортимент":
        await send_or_edit(message.bot, message.chat.id, user_id, "Текущий ассортимент:",
                           reply_markup=get_admin_assortment_keyboard())

    elif text == "Редактировать цену доставки":
        await send_or_edit(message.bot, message.chat.id, user_id, f"Текущая цена доставки: {DELIVERY_FEE}₽\nВведите новую цену:",
                           reply_markup=ForceReply())
        admin_states[user_id] = {"state": "editing_delivery_fee"}

    elif text == "Активные заказы":
        if active_orders:
            buttons = []
            for order_id, order in active_orders.items():
                buttons.append([InlineKeyboardButton(text=f"{order['product']['name']} от {order['user_id']}",
                                       callback_data=f"active_order_{order["user_id"]}")])
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_back_to_menu")])

            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            await send_or_edit(message.bot, message.chat.id, user_id, "Список активных заказов:", reply_markup=kb)
        else:
            await send_or_edit(message.bot, message.chat.id, user_id, "Нет активных заказов.")

    elif text == "Выйти из админки":
        await send_or_edit(message.bot, message.chat.id, user_id, "Выход из админки", reply_markup=ReplyKeyboardRemove())
        await send_or_edit(message.bot,
                           message.chat.id, user_id,
                           "Добро пожаловать! Выберите опцию:",
                           reply_markup=main_menu_keyboard
                           )
        active_admins[user_id] = False
        admin_states.pop(user_id, None)


@router.message(lambda message: str(message.from_user.id) in admin_ids and message.text == "Выйти из диалога")
async def admin_exit_chat_handler(message: Message):
    user_id = message.from_user.id
    partner_id = active_conversations.get(user_id)
    if partner_id:
        await message.bot.send_message(partner_id, "Администратор завершил диалог.")
        active_conversations.pop(user_id, None)
        active_conversations.pop(partner_id, None)
        user_data[user_id]["in_chat"] = False
        user_data[partner_id]["in_chat"] = False
        await send_or_edit(message.bot, message.chat.id, user_id, "Вы вышли из диалога.", reply_markup=admin_menu_reply)
    else:
        await send_or_edit(message.bot, message.chat.id, user_id, "Вы не в диалоге.")
