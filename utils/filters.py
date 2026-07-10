from aiogram import Bot
from aiogram.types import User
from config import OWNER_ID
from database import db


async def is_admin(user_id: int) -> bool:
    """Foydalanuvchi bosh admin yoki qo'shilgan admin ekanini tekshiradi."""
    if user_id == OWNER_ID:
        return True
    admins = await db.get_all_admins()
    return user_id in admins


async def check_force_sub(bot: Bot, user_id: int) -> list:
    """
    Foydalanuvchi barcha majburiy kanallarga a'zo bo'lganini tekshiradi.
    Qaytaradi: a'zo BO'LMAGAN kanallar ro'yxati (bo'sh bo'lsa - hammasiga a'zo).

    Premium foydalanuvchilar majburiy obunadan ozod qilingan - ular uchun
    har doim bo'sh ro'yxat qaytariladi (ya'ni tekshiruv o'tkazib yuboriladi).
    """
    if await db.is_premium(user_id):
        return []

    channels = await db.get_force_sub_channels()
    not_joined = []

    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except Exception:
            # Bot kanalda admin bo'lmasa yoki kanal topilmasa ham
            # foydalanuvchini bloklamaslik uchun o'tkazib yuboramiz,
            # lekin bu holatni adminlarga alohida ko'rsatish tavsiya etiladi.
            not_joined.append(ch)

    return not_joined
