import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import API_TOKEN
import handlers
from keyboards.user_keyboards import main_menu_keyboard
from state import user_data, send_or_edit

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(handlers.get_routers())


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())