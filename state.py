import redis

from config import ADMINS_ID
from services.redis_storage import RedisDict

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

user_data = RedisDict(redis_client, "user_data")
payment_requests = RedisDict(redis_client, "payment_requests")
admin_states = RedisDict(redis_client, "admin_states")
active_orders = RedisDict(redis_client, "active_orders")
active_conversations = RedisDict(redis_client, "active_conversations")
active_admins = RedisDict(redis_client, "active_admins")
saved_addresses = RedisDict(redis_client, "saved_addresses")
assortment = RedisDict(redis_client, "assortment")
admin_ids = ADMINS_ID

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
