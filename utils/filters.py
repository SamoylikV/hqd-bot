from aiogram.filters import Filter
from aiogram.types import Message
from state import active_conversations


class UserNotInConversation(Filter):
    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id
        for conv in active_conversations.values():
            if user_id == conv:
                return False
        return True

class AdminNotInConversation(Filter):
    async def __call__(self, message: Message) -> bool:
        admin_id = message.from_user.id
        for conv in active_conversations.values():
            if admin_id == conv:
                return False
        return True