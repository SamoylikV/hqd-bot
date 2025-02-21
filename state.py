user_data = {}
admin_ids = []
admin_states = {}
active_orders = {}
active_conversations = {}
saved_addresses = {}
assortment = {
    "1": {"name": "Товар1", "base_price": 2400, "flavors": ["Клубника", "Банан"]},
    "2": {"name": "Товар2", "base_price": 1500, "flavors": ["Ваниль", "Шоколад"]},
    "3": {"name": "Товар3", "base_price": 2000, "flavors": ["Мята", "Ваниль", "Клубника"]},
}

async def send_or_edit(bot, chat_id: int, user_id: int, text: str, reply_markup=None):
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
