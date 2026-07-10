from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_USERNAME


def force_sub_keyboard(channels):
    """Majburiy obuna uchun kanal linklari + 'Tekshirish' tugmasi."""
    builder = InlineKeyboardBuilder()
    for ch in channels:
        link = ch["invite_link"] or f"https://t.me/{str(ch['chat_id']).lstrip('@')}"
        builder.row(InlineKeyboardButton(text=f"➕ {ch['title']}", url=link))
    builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
    return builder.as_markup()


def premium_keyboard():
    """Premium sotib olish uchun to'g'ridan-to'g'ri admin bilan bog'lanish linki."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="💳 Premium sotib olish",
        url=f"https://t.me/{ADMIN_USERNAME}"
    ))
    return builder.as_markup()


def search_results_keyboard(movies, is_user_premium: bool, free_limit: int):
    """Nom bo'yicha qidiruv natijalari - kod bilan tez ochish tugmalari."""
    builder = InlineKeyboardBuilder()
    shown = movies if is_user_premium else movies[:free_limit]
    for m in shown:
        builder.row(InlineKeyboardButton(text=f"🎬 {m['title']}", callback_data=f"get_{m['code']}"))
    if not is_user_premium and len(movies) > free_limit:
        builder.row(InlineKeyboardButton(
            text=f"🔒 Yana {len(movies) - free_limit} ta natija (Premium kerak)",
            callback_data="premium_info"
        ))
    return builder.as_markup()


def tmdb_suggestions_keyboard(suggestions):
    """TMDB'dan topilgan takliflar uchun 'So'rash' tugmalari."""
    builder = InlineKeyboardBuilder()
    for i, s in enumerate(suggestions):
        year_part = f" ({s['year']})" if s.get("year") else ""
        label = f"📩 {s['title']}{year_part} - So'rash"
        builder.row(InlineKeyboardButton(text=label, callback_data=f"req_{i}"))
    return builder.as_markup()


def my_requests_keyboard(requests):
    """Foydalanuvchining kutilayotgan so'rovlari - har biri 'Bekor qilish' tugmasi bilan."""
    builder = InlineKeyboardBuilder()
    for r in requests:
        year_part = f" ({r['query_year']})" if r["query_year"] else ""
        builder.row(InlineKeyboardButton(
            text=f"❌ {r['query_title']}{year_part}",
            callback_data=f"delreq_{r['id']}"
        ))
    return builder.as_markup()


def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"))
    builder.row(InlineKeyboardButton(text="📩 Kutilayotgan so'rovlar", callback_data="adm_requests"))
    builder.row(InlineKeyboardButton(text="📢 Xabar yuborish (Broadcast)", callback_data="adm_broadcast"))
    builder.row(InlineKeyboardButton(text="🎬 Kino qo'shish", callback_data="adm_add_movie"),
                InlineKeyboardButton(text="🗑 Kino o'chirish", callback_data="adm_del_movie"))
    builder.row(InlineKeyboardButton(text="📡 Majburiy obuna kanallar", callback_data="adm_fsub"))
    builder.row(InlineKeyboardButton(text="👑 Premium berish/olib qo'yish", callback_data="adm_premium"))
    builder.row(InlineKeyboardButton(text="🛡 Adminlar", callback_data="adm_admins"))
    return builder.as_markup()


def fsub_panel_keyboard(channels):
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(InlineKeyboardButton(text=f"❌ {ch['title']} ni o'chirish", callback_data=f"fsub_del_{ch['chat_id']}"))
    builder.row(InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="fsub_add"))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return builder.as_markup()


def cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action"))
    return builder.as_markup()


def back_to_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return builder.as_markup()
