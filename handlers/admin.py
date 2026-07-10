import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import STORAGE_CHANNEL_ID, OWNER_ID
from database import db
from utils.filters import is_admin
from utils.states import DeleteMovie, Broadcast, FSubAdd, PremiumManage, AdminManage
from keyboards.inline import (
    admin_panel_keyboard, fsub_panel_keyboard, cancel_keyboard, back_to_admin_keyboard
)

router = Router()


# ---------- Kirish nuqtasi ----------

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message.from_user.id):
        return
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=admin_panel_keyboard())


@router.callback_query(F.data == "adm_back")
async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛠 <b>Admin panel</b>", reply_markup=admin_panel_keyboard())
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.", reply_markup=admin_panel_keyboard())
    await callback.answer()


# ---------- Statistika ----------

@router.callback_query(F.data == "adm_stats")
async def cb_stats(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    stats = await db.get_stats()
    pending = await db.get_pending_requests_count()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🆕 Bugun qo'shilganlar: <b>{stats['today_users']}</b>\n"
        f"⭐️ Premium foydalanuvchilar: <b>{stats['total_premium']}</b>\n"
        f"🎬 Jami kinolar: <b>{stats['total_movies']}</b>\n"
        f"📩 Kutilayotgan so'rovlar: <b>{pending}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm_requests")
async def cb_pending_requests(callback: CallbackQuery):
    """Admin uchun: barcha kutilayotgan so'rovlar ro'yxati (premium birinchi)."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer()

    requests = await db.get_pending_requests(limit=30)

    if not requests:
        await callback.message.edit_text(
            "📩 <b>Kutilayotgan so'rovlar</b>\n\nHozircha hech kim hech narsa so'ramagan.",
            reply_markup=back_to_admin_keyboard()
        )
        await callback.answer()
        return

    text = "📩 <b>Kutilayotgan so'rovlar</b>\n\n"
    for r in requests:
        year_part = f" ({r['query_year']})" if r["query_year"] else ""
        mark = "⭐️ " if r["is_priority"] else "• "
        text += f"{mark}{r['query_title']}{year_part}\n"

    text += (
        "\nKino qo'shganingizda «Nomi:» ni yuqoridagi nomlarga imkon qadar "
        "yaqin yozing — shunda so'ragan foydalanuvchilarga avtomatik xabar ketadi."
    )

    await callback.message.edit_text(text, reply_markup=back_to_admin_keyboard())
    await callback.answer()


# ---------- Kino qo'shish ----------
# YANGI USUL: Admin videoni to'g'ridan-to'g'ri SAQLASH KANALIGA yuboradi,
# caption (izoh) ichida "Kod:" va "Nomi:" yozadi. Bot kanalni kuzatib
# turadi (handlers/channel.py) va avtomatik bazaga saqlaydi.
# Botga alohida video yuborish shart emas.

@router.callback_query(F.data == "adm_add_movie")
async def cb_add_movie_info(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    await callback.message.edit_text(
        "🎬 <b>Kino qo'shish</b>\n\n"
        "Kino qo'shish uchun botga hech narsa yuborish shart emas!\n\n"
        "Shunchaki saqlash kanaliga (bot admin bo'lgan kanalga) video yoki "
        "faylni yuklang va <b>izoh (caption)</b> qismiga quyidagi formatda yozing:\n\n"
        "<code>Kod: 1024\nNomi: Titanik</code>\n\n"
        "Bot buni avtomatik o'qib, bazaga saqlaydi. Bir nechta kinoni ketma-ket "
        "shu tarzda yuklashingiz mumkin.\n\n"
        "❗️ Kod va Nomi alohida qatorda, yuqoridagi formatda bo'lishi shart.",
        reply_markup=back_to_admin_keyboard()
    )
    await callback.answer()


# ---------- Kino o'chirish ----------

@router.callback_query(F.data == "adm_del_movie")
async def cb_del_movie_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(DeleteMovie.waiting_for_code)
    await callback.message.edit_text(
        "🗑 O'chirmoqchi bo'lgan kino kodini yuboring:",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(DeleteMovie.waiting_for_code, F.text)
async def del_movie_receive_code(message: Message, state: FSMContext):
    code = message.text.strip()
    ok = await db.delete_movie(code)
    await state.clear()
    if ok:
        await message.answer(f"✅ <code>{code}</code> kodli kino o'chirildi.", reply_markup=admin_panel_keyboard())
    else:
        await message.answer(f"❌ <code>{code}</code> kodli kino topilmadi.", reply_markup=admin_panel_keyboard())


# ---------- Broadcast (xabar yuborish) ----------

@router.callback_query(F.data == "adm_broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(Broadcast.waiting_for_message)
    await callback.message.edit_text(
        "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring "
        "(matn, rasm, video — istalgan turdagi xabar bo'lishi mumkin):",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(Broadcast.waiting_for_message)
async def broadcast_receive_message(message: Message, state: FSMContext):
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(Broadcast.waiting_for_confirm)
    await message.answer(
        "⬆️ Xabar shu ko'rinishda yuboriladi. Tasdiqlaysizmi?\n\n"
        "Tasdiqlash uchun <b>ha</b>, bekor qilish uchun <b>yo'q</b> deb yozing."
    )


@router.message(Broadcast.waiting_for_confirm, F.text)
async def broadcast_confirm(message: Message, state: FSMContext, bot: Bot):
    if message.text.strip().lower() not in ("ha", "yes", "ha."):
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_panel_keyboard())
        return

    data = await state.get_data()
    user_ids = await db.get_all_user_ids()
    await state.clear()

    status_msg = await message.answer(f"⏳ Yuborilmoqda... 0/{len(user_ids)}")

    sent, failed = 0, 0
    for i, uid in enumerate(user_ids, start=1):
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=data["chat_id"], message_id=data["message_id"])
            sent += 1
        except Exception:
            failed += 1
        if i % 30 == 0:
            await asyncio.sleep(1)  # Telegram flood-limitidan saqlanish
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... {i}/{len(user_ids)}")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ <b>Broadcast tugadi!</b>\n\n📨 Yuborildi: {sent}\n❌ Xatolik: {failed}"
    )
    await message.answer("🛠 Admin panel", reply_markup=admin_panel_keyboard())


# ---------- Majburiy obuna kanallari ----------

@router.callback_query(F.data == "adm_fsub")
async def cb_fsub_panel(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    channels = await db.get_force_sub_channels()
    text = "📡 <b>Majburiy obuna kanallari</b>\n\n"
    text += "\n".join([f"• {ch['title']} (<code>{ch['chat_id']}</code>)" for ch in channels]) or "Hozircha kanal qo'shilmagan."
    await callback.message.edit_text(text, reply_markup=fsub_panel_keyboard(channels))
    await callback.answer()


@router.callback_query(F.data == "fsub_add")
async def cb_fsub_add_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(FSubAdd.waiting_for_channel)
    await callback.message.edit_text(
        "➕ Yangi majburiy obuna kanalini qo'shish.\n\n"
        "Botni shu kanalga <b>admin</b> qilib qo'shing, so'ng kanalning "
        "<b>username</b>'ini (masalan: <code>@mychannel</code>) yoki "
        "<b>ID raqamini</b> (masalan: <code>-1001234567890</code>) yuboring:",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(FSubAdd.waiting_for_channel, F.text)
async def fsub_add_receive(message: Message, state: FSMContext, bot: Bot):
    chat_id_input = message.text.strip()

    try:
        chat = await bot.get_chat(chat_id_input)
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status not in ("administrator", "creator"):
            await message.answer(
                "⚠️ Bot bu kanalda admin emas. Iltimos, botni admin qiling va qaytadan urinib ko'ring."
            )
            return

        invite_link = chat.invite_link or ""
        if not invite_link:
            try:
                link_obj = await bot.create_chat_invite_link(chat.id)
                invite_link = link_obj.invite_link
            except Exception:
                invite_link = f"https://t.me/{chat.username}" if chat.username else ""

        await db.add_force_sub_channel(str(chat.id), chat.title or chat_id_input, invite_link)
        await state.clear()
        await message.answer(
            f"✅ <b>{chat.title}</b> majburiy obuna ro'yxatiga qo'shildi!",
            reply_markup=admin_panel_keyboard()
        )
    except Exception as e:
        await message.answer(
            f"⚠️ Xatolik: {e}\n\nKanal username/ID to'g'riligini va bot admin ekanligini tekshiring."
        )


@router.callback_query(F.data.startswith("fsub_del_"))
async def cb_fsub_delete(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    chat_id = callback.data.removeprefix("fsub_del_")
    await db.remove_force_sub_channel(chat_id)
    channels = await db.get_force_sub_channels()
    text = "📡 <b>Majburiy obuna kanallari</b>\n\n"
    text += "\n".join([f"• {ch['title']} (<code>{ch['chat_id']}</code>)" for ch in channels]) or "Hozircha kanal qo'shilmagan."
    await callback.message.edit_text(text, reply_markup=fsub_panel_keyboard(channels))
    await callback.answer("✅ Kanal o'chirildi")


# ---------- Premium boshqarish ----------

@router.callback_query(F.data == "adm_premium")
async def cb_premium_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(PremiumManage.waiting_for_user_id)
    await callback.message.edit_text(
        "👑 Premium bermoqchi bo'lgan foydalanuvchi ID raqamini yuboring.\n\n"
        "Olib qo'yish uchun ID dan keyin <b>0</b> kun deb yozasiz (keyingi qadamda).",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(PremiumManage.waiting_for_user_id, F.text)
async def premium_receive_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❗️ Iltimos, to'g'ri ID raqam yuboring.")
        return
    await state.update_data(user_id=user_id)
    await state.set_state(PremiumManage.waiting_for_days)
    await message.answer(
        "📅 Necha kunlik premium berasiz? (Olib qo'yish uchun <b>0</b> yuboring):"
    )


@router.message(PremiumManage.waiting_for_days, F.text)
async def premium_receive_days(message: Message, state: FSMContext, bot: Bot):
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("❗️ Iltimos, son yuboring.")
        return

    data = await state.get_data()
    user_id = data["user_id"]
    await state.clear()

    if days <= 0:
        await db.remove_premium(user_id)
        await message.answer(f"✅ {user_id} foydalanuvchining premiumi olib qo'yildi.", reply_markup=admin_panel_keyboard())
        try:
            await bot.send_message(user_id, "ℹ️ Sizning premium obunangiz bekor qilindi.")
        except Exception:
            pass
    else:
        until = await db.set_premium(user_id, days)
        await message.answer(
            f"✅ {user_id} foydalanuvchiga {days} kunlik premium berildi.",
            reply_markup=admin_panel_keyboard()
        )
        try:
            await bot.send_message(
                user_id,
                f"🎉 Sizga {days} kunlik <b>Premium</b> obuna berildi! Endi barcha imkoniyatlardan foydalanishingiz mumkin."
            )
        except Exception:
            pass


# ---------- Adminlarni boshqarish (faqat OWNER) ----------

@router.callback_query(F.data == "adm_admins")
async def cb_admins_panel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("⛔️ Bu funksiya faqat bosh admin uchun.", show_alert=True)
    admins = await db.get_all_admins()
    text = "🛡 <b>Adminlar ro'yxati</b>\n\n"
    text += "\n".join([f"• <code>{a}</code>" for a in admins]) or "Qo'shimcha admin yo'q."
    text += "\n\nYangi admin qo'shish uchun ID yuboring, o'chirish uchun oldiga <b>-</b> qo'yib yuboring (masalan: <code>-123456</code>):"
    await state.set_state(AdminManage.waiting_for_user_id)
    await callback.message.edit_text(text, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminManage.waiting_for_user_id, F.text)
async def admins_manage_receive(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    text = message.text.strip()
    await state.clear()

    try:
        if text.startswith("-"):
            user_id = int(text[1:])
            await db.remove_admin(user_id)
            await message.answer(f"✅ {user_id} adminlikdan olindi.", reply_markup=admin_panel_keyboard())
        else:
            user_id = int(text)
            await db.add_admin(user_id, message.from_user.id)
            await message.answer(f"✅ {user_id} admin qilib tayinlandi.", reply_markup=admin_panel_keyboard())
    except ValueError:
        await message.answer("❗️ Noto'g'ri format.", reply_markup=admin_panel_keyboard())
