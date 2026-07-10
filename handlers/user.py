from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from config import (
    STORAGE_CHANNEL_ID, FREE_SEARCH_LIMIT, FREE_DAILY_DOWNLOAD_LIMIT,
    PREMIUM_PRICE_TEXT, ADMIN_USERNAME
)
from database import db
from utils.filters import check_force_sub
from utils.tmdb import search_tmdb
from keyboards.inline import (
    force_sub_keyboard, premium_keyboard,
    search_results_keyboard, tmdb_suggestions_keyboard, my_requests_keyboard
)
from keyboards.reply import (
    main_reply_keyboard, BTN_SEARCH, BTN_PREMIUM, BTN_HELP, BTN_MY_REQUESTS
)

router = Router()

# TMDB qidiruv natijalarini vaqtinchalik saqlash uchun (callback_data uzun
# bo'lmasligi kerak, shuning uchun to'liq ma'lumotni RAM'da ushlab turamiz).
# Format: {user_id: {"0": {...}, "1": {...}}}
_tmdb_cache: dict[int, dict[str, dict]] = {}


WELCOME_TEXT = (
    "🎬 <b>Kino botga xush kelibsiz!</b>\n\n"
    "Kino kodini yuboring — men sizga filmni topib beraman.\n"
    "Yoki kino nomini yozib, qidirishingiz ham mumkin.\n\n"
    "Masalan: <code>1024</code> yoki <code>Titanik</code>\n\n"
    "Pastdagi menyudan ham foydalanishingiz mumkin 👇"
)

HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "• Kino kodini yuboring — filmni olasiz\n"
    "• Kino nomini yozing — qidiruv natijalari chiqadi\n"
    "• 📩 Mening so'rovlarim — so'ragan kinolaringiz holatini ko'rish\n"
    "• /start — botni qayta ishga tushirish\n"
    f"• Savol bo'lsa — @{ADMIN_USERNAME} ga yozing"
)


async def send_force_sub_message(message: Message):
    channels = await db.get_force_sub_channels()
    text = (
        "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling</b>, "
        "so'ng «✅ Tekshirish» tugmasini bosing:"
    )
    await message.answer(text, reply_markup=force_sub_keyboard(channels))


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    await db.add_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or ""
    )

    not_joined = await check_force_sub(bot, message.from_user.id)
    if not_joined:
        await send_force_sub_message(message)
        return

    await message.answer(WELCOME_TEXT, reply_markup=main_reply_keyboard())


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery, bot: Bot):
    not_joined = await check_force_sub(bot, callback.from_user.id)
    if not_joined:
        await callback.answer("❌ Siz hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
        return
    await callback.message.delete()
    await callback.message.answer(WELCOME_TEXT, reply_markup=main_reply_keyboard())
    await callback.answer("✅ Tabriklaymiz, endi botdan foydalanishingiz mumkin!")


async def send_premium_info(message: Message):
    text = (
        "⭐️ <b>Premium obuna</b>\n\n"
        "Premium bilan siz:\n"
        f"• Kino nomi bo'yicha qidirganda <b>barcha</b> natijalarni ko'rasiz (bepulda faqat {FREE_SEARCH_LIMIT} ta)\n"
        f"• Kunlik yuklab olish <b>cheksiz</b> (bepulda kuniga {FREE_DAILY_DOWNLOAD_LIMIT} ta)\n"
        "• Majburiy obuna kanallariga a'zo bo'lmasangiz ham botdan foydalanasiz\n"
        "• So'ragan kinolaringiz <b>birinchi navbatda</b> ko'rib chiqiladi\n\n"
        f"💳 Narxi: <b>{PREMIUM_PRICE_TEXT}</b>\n\n"
        f"Sotib olish uchun quyidagi tugma orqali @{ADMIN_USERNAME} ga yozing:"
    )
    await message.answer(text, reply_markup=premium_keyboard())


@router.message(F.text == BTN_PREMIUM)
async def handle_premium_button(message: Message):
    await send_premium_info(message)


@router.callback_query(F.data == "premium_info")
async def cb_premium_info(callback: CallbackQuery):
    await send_premium_info(callback.message)
    await callback.answer()


@router.message(F.text == BTN_HELP)
async def handle_help_button(message: Message):
    await message.answer(HELP_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)


@router.message(F.text == BTN_SEARCH)
async def handle_search_button(message: Message):
    """
    Telegram pastki (Reply Keyboard) tugmalari qidiruv oynasini avtomatik
    ochib bera olmaydi - shuning uchun foydalanuvchiga oddiy yo'riqnoma
    beramiz: kod yoki nomni to'g'ridan-to'g'ri shu yerga yozadi.
    """
    await message.answer(
        "🔍 Qidirish uchun kino <b>kodini</b> yoki <b>nomini</b> yozib yuboring.\n\n"
        "Masalan: <code>1024</code> yoki <code>Titanik</code>"
    )


async def render_my_requests(user_id: int):
    """'Mening so'rovlarim' matni va klaviaturasini tayyorlaydi (ikkala joyda ishlatiladi)."""
    all_requests = await db.get_user_requests(user_id)
    pending = [r for r in all_requests if not r["notified"]]
    done = [r for r in all_requests if r["notified"]]

    text = "📩 <b>Mening so'rovlarim</b>\n\n"

    if not all_requests:
        text += (
            "Hozircha hech narsa so'ramagansiz.\n\n"
            "Qidirganingiz kino bazamizda topilmasa, taklif ostidagi "
            "«So'rash» tugmasini bosing — shu yerda kuzatib borasiz."
        )
        return text, None

    if pending:
        text += f"⏳ <b>Kutilmoqda ({len(pending)} ta):</b>\n"
        for r in pending:
            year_part = f" ({r['query_year']})" if r["query_year"] else ""
            mark = " ⭐️" if r["is_priority"] else ""
            text += f"• {r['query_title']}{year_part}{mark}\n"
        text += "\n"

    if done:
        text += f"✅ <b>Qo'shilgan ({len(done)} ta):</b>\n"
        for r in done[:10]:
            year_part = f" ({r['query_year']})" if r["query_year"] else ""
            text += f"• {r['query_title']}{year_part}\n"
        text += "\n"

    text += (
        "ℹ️ Diqqat: barcha manbalardan qidiramiz, lekin har bir kinoni 100% "
        "topib bera olishimizga kafolat yo'q."
    )

    keyboard = my_requests_keyboard(pending) if pending else None
    return text, keyboard


@router.message(F.text == BTN_MY_REQUESTS)
async def handle_my_requests_button(message: Message):
    text, keyboard = await render_my_requests(message.from_user.id)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command("my_requests"))
async def cmd_my_requests(message: Message):
    text, keyboard = await render_my_requests(message.from_user.id)
    await message.answer(text, reply_markup=keyboard)


async def send_tmdb_suggestions(message: Message, query: str):
    """
    O'z bazamizda kino topilmasa, TMDB'dan taklif ko'rsatadi.
    Bu FAYL EMAS, faqat "bunday kino bor ekan, lekin bizda hali yo'q"
    degan ma'lumot - foydalanuvchi kod bilan olishga urina olmaydi.
    Har bir taklif ostida "So'rash" tugmasi bo'ladi - bosilsa, so'rov
    saqlanadi va kino keyin qo'shilganda foydalanuvchiga avtomatik xabar boradi.
    """
    suggestions = await search_tmdb(query)

    if not suggestions:
        await message.answer(
            "😕 Hech narsa topilmadi. Kodni tekshirib ko'ring yoki boshqa nom bilan qidiring."
        )
        return

    text = (
        f"😕 <b>«{query}»</b> bizning bazamizda topilmadi.\n\n"
        "Lekin bunday nomlar mavjud ekan. Kerakli kinoni tanlang — biz uni "
        "qo'shganimizda sizga <b>avtomatik xabar beramiz</b>.\n\n"
        "ℹ️ Biz barcha manbalardan qidiramiz, lekin har bir kinoni 100% "
        "topib bera olishimizga kafolat yo'q."
    )

    # Natijalarni keshga joylaymiz, callback_data faqat indeks tashiydi
    _tmdb_cache[message.from_user.id] = {str(i): s for i, s in enumerate(suggestions)}

    await message.answer(text, reply_markup=tmdb_suggestions_keyboard(suggestions))


async def deliver_movie(message_or_callback, bot: Bot, code: str, user_id: int):
    """Kanaldan kinoni topib, forward qilib beradi va ko'rishlar sonini oshiradi."""
    movie = await db.get_movie_by_code(code)
    if not movie:
        return False, "not_found"

    # Kunlik limit tekshiruvi (faqat oddiy foydalanuvchilar uchun, premium cheksiz)
    user_premium = await db.is_premium(user_id)
    if not user_premium:
        used = await db.get_daily_downloads(user_id)
        if used >= FREE_DAILY_DOWNLOAD_LIMIT:
            return False, "limit_reached"

    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=STORAGE_CHANNEL_ID,
            message_id=movie["channel_message_id"],
            caption=f"🎬 <b>{movie['title']}</b>\n\n🔗 Kod: <code>{movie['code']}</code>",
            parse_mode="HTML"
        )
        await db.increment_views(code)
        if not user_premium:
            await db.increment_daily_downloads(user_id)
        return True, "ok"
    except Exception as e:
        target = message_or_callback if isinstance(message_or_callback, Message) else message_or_callback.message
        await target.answer(f"⚠️ Kinoni yuborishda xatolik yuz berdi: {e}")
        return False, "error"


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, bot: Bot):
    not_joined = await check_force_sub(bot, message.from_user.id)
    if not_joined:
        await send_force_sub_message(message)
        return

    query = message.text.strip()

    # 1) Avval aniq kod sifatida qidiramiz
    movie = await db.get_movie_by_code(query)
    if movie:
        ok, reason = await deliver_movie(message, bot, query, message.from_user.id)
        if ok:
            await db.increment_search_count(message.from_user.id)
        elif reason == "limit_reached":
            await message.answer(
                f"⛔️ Kunlik bepul limit ({FREE_DAILY_DOWNLOAD_LIMIT} ta) tugadi.\n\n"
                "Cheksiz yuklab olish uchun Premium sotib oling.",
                reply_markup=premium_keyboard()
            )
        return

    # 2) Topilmasa - nom bo'yicha o'z bazamizdan qidiruv
    results = await db.search_movies_by_title(query)
    if not results:
        await send_tmdb_suggestions(message, query)
        return

    user_premium = await db.is_premium(message.from_user.id)
    await db.increment_search_count(message.from_user.id)

    text = f"🔎 <b>«{query}»</b> bo'yicha {len(results)} ta natija topildi:"
    await message.answer(
        text,
        reply_markup=search_results_keyboard(results, user_premium, FREE_SEARCH_LIMIT)
    )


@router.callback_query(F.data.startswith("get_"))
async def cb_get_movie(callback: CallbackQuery, bot: Bot):
    code = callback.data.removeprefix("get_")
    ok, reason = await deliver_movie(callback, bot, code, callback.from_user.id)
    if ok:
        await callback.answer("✅ Yuborildi!")
    elif reason == "limit_reached":
        await callback.answer(
            f"⛔️ Kunlik bepul limit ({FREE_DAILY_DOWNLOAD_LIMIT} ta) tugadi. "
            "Cheksiz yuklab olish uchun Premium sotib oling.",
            show_alert=True
        )
    else:
        await callback.answer("❌ Topilmadi.", show_alert=True)


@router.callback_query(F.data.startswith("req_"))
async def cb_request_movie(callback: CallbackQuery):
    """
    Foydalanuvchi TMDB taklifidan 'So'rash' tugmasini bosganda ishga tushadi.
    So'rov bazaga yoziladi - kino keyin qo'shilganda shu foydalanuvchiga
    avtomatik xabar boradi (handlers/channel.py da amalga oshiriladi).
    """
    idx = callback.data.removeprefix("req_")
    data = _tmdb_cache.get(callback.from_user.id)

    if not data or idx not in data:
        await callback.answer("⚠️ So'rov muddati tugagan, qaytadan qidiring.", show_alert=True)
        return

    suggestion = data[idx]
    user_premium = await db.is_premium(callback.from_user.id)
    added = await db.add_movie_request(
        callback.from_user.id,
        suggestion["title"],
        suggestion.get("year", ""),
        is_priority=user_premium
    )

    if added:
        extra = "\n\n⭐️ Premium sifatida so'rovingiz birinchi navbatda ko'riladi." if user_premium else ""
        await callback.answer(
            "✅ So'rovingiz qabul qilindi! Kino qo'shilganda sizga avtomatik xabar boramiz.\n\n"
            "ℹ️ Diqqat: barcha manbalardan qidiramiz, lekin har bir kinoni 100% "
            "topib bera olishimizga kafolat yo'q." + extra,
            show_alert=True
        )
    else:
        await callback.answer("ℹ️ Siz bu kinoni allaqachon so'ragansiz.", show_alert=True)


@router.callback_query(F.data.startswith("delreq_"))
async def cb_delete_request(callback: CallbackQuery):
    """Foydalanuvchi o'z so'rovini ro'yxatdan bekor qiladi."""
    request_id = int(callback.data.removeprefix("delreq_"))
    ok = await db.delete_user_request(request_id, callback.from_user.id)

    if not ok:
        await callback.answer("⚠️ So'rov topilmadi.", show_alert=True)
        return

    text, keyboard = await render_my_requests(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("✅ So'rov bekor qilindi.")
