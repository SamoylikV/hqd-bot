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