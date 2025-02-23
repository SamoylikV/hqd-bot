from state import user_data


async def send_or_edit(bot, chat_id: int, user_id: int, text: str, reply_markup=None, parse_mode=None):
    if parse_mode == "HTML":
        text = text.replace("<br>", "\n").replace("<br/>", "\n")

    last_msg_id = user_data.get(user_id, {}).get("last_message_id")
    if last_msg_id:
        try:
            await bot.edit_message_text(text, chat_id, last_msg_id, reply_markup=reply_markup, parse_mode=parse_mode)
            return last_msg_id
        except Exception:
            try:
                await bot.delete_message(chat_id, last_msg_id)
            except Exception:
                pass
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    user_data.setdefault(user_id, {})["last_message_id"] = msg.message_id
    return msg.message_id
