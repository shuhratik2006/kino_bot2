import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers import admin, user, channel

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi! .env faylini sozlang.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    await init_db()

    # Admin handlerlari user handlerlaridan OLDIN ro'yxatga olinishi kerak,
    # aks holda matnli xabarlar (FSM holatlaridagi) user.py dagi umumiy
    # matn handleriga tushib qolishi mumkin.
    dp.include_router(admin.router)
    dp.include_router(channel.router)
    dp.include_router(user.router)

    logging.info("Bot ishga tushdi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
