from aiogram.filters import Filter
from aiogram.types import Message
from state import active_conversations, active_admins


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

class AdminNotInMenu(Filter):
    async def __call__(self, message: Message) -> bool:
        admin_id = message.from_user.id
        for active_admin, value in active_admins.items():
            if active_admin == str(admin_id) and value:
                return False
        return True