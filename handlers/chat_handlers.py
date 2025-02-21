from aiogram import Router
from aiogram.types import Message

from keyboards.admin_keyboards import get_admin_exit_reply_keyboard
from state import user_data, admin_ids, active_conversations

router = Router(name="chat_handlers")


def start_conversation(admin_id: int, customer_id: int):
    active_conversations[customer_id] = admin_id
    active_conversations[admin_id] = customer_id
    user_data.setdefault(customer_id, {})["in_chat"] = True
    user_data.setdefault(admin_id, {})["in_chat"] = True




@router.message(
    lambda message: message.from_user.id not in admin_ids and message.from_user.id in user_data and user_data.get(
        message.from_user.id, {}).get("in_chat"))
async def customer_chat_handler(message: Message):
    partner = active_conversations.get(message.from_user.id)
    if partner:
        await message.bot.send_message(partner, message.text,
                                       reply_markup=get_admin_exit_reply_keyboard() if partner in admin_ids else None)
