import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import API_TOKEN
import handlers

logging.basicConfig(level=logging.INFO)



async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()
    dp.include_router(handlers.get_routers())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())