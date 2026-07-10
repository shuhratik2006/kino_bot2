from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


# Foydalanuvchi uchun pastki doimiy menyu tugmalari.
# Bular oddiy matn sifatida keladi (handlers/user.py da F.text bilan ushlanadi).
BTN_SEARCH = "🔍 Kino qidirish"
BTN_PREMIUM = "⭐️ Premium"
BTN_HELP = "ℹ️ Yordam"
BTN_MY_REQUESTS = "📩 Mening so'rovlarim"


def main_reply_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=BTN_SEARCH))
    builder.row(KeyboardButton(text=BTN_PREMIUM), KeyboardButton(text=BTN_HELP))
    builder.row(KeyboardButton(text=BTN_MY_REQUESTS))
    return builder.as_markup(resize_keyboard=True, is_persistent=True)
