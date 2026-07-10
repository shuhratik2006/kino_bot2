import re
from aiogram import Router, F, Bot
from aiogram.types import Message

from config import STORAGE_CHANNEL_ID
from database import db

router = Router()


def parse_caption(caption: str):
    """
    Caption ichidan kod va nomni ajratib oladi.
    Kutilgan format:
        Kod: 1024
        Nomi: Titanik
    Katta-kichik harf va bo'sh joylarga sezgir emas.
    """
    if not caption:
        return None, None

    code_match = re.search(r"kod\s*:\s*(.+)", caption, re.IGNORECASE)
    title_match = re.search(r"nomi\s*:\s*(.+)", caption, re.IGNORECASE)

    code = code_match.group(1).strip().split("\n")[0].strip() if code_match else None
    title = title_match.group(1).strip().split("\n")[0].strip() if title_match else None

    return code, title


async def notify_requesters(bot: Bot, title: str, code: str):
    """
    Yangi qo'shilgan kino nomiga mos so'rov qoldirgan foydalanuvchilarni
    topib, ularga avtomatik xabar va kodni yuboradi.
    """
    matches = await db.find_matching_requests(title)
    if not matches:
        return

    notified_ids = []
    for req in matches:
        try:
            await bot.send_message(
                chat_id=req["user_id"],
                text=(
                    f"🎉 Siz so'ragan kino qo'shildi!\n\n"
                    f"🎬 <b>{title}</b>\n"
                    f"🔗 Kod: <code>{code}</code>\n\n"
                    f"Kodni botga yuborib, kinoni olishingiz mumkin."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass  # foydalanuvchi botni bloklagan bo'lishi mumkin
        notified_ids.append(req["id"])

    await db.mark_requests_notified(notified_ids)


async def save_movie_from_channel(message: Message, bot: Bot, is_edit: bool = False):
    """
    Kanal postidan (yangi yoki tahrirlangan) kino ma'lumotini o'qib,
    bazaga saqlaydi, tasdiq xabarini yozadi va mos so'rovlarga xabar beradi.
    """
    code, title = parse_caption(message.caption or "")

    if not code:
        if not is_edit:
            # Faqat yangi post uchun ogohlantirish yozamiz;
            # tahrirlashda ogohlantirish keraksiz shovqin bo'ladi.
            try:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=(
                        "⚠️ Bu post uchun kod topilmadi, shuning uchun bazaga saqlanmadi.\n\n"
                        "Iltimos, izohga quyidagi formatda yozing:\n"
                        "Kod: 1024\nNomi: Titanik\n\n"
                        "Va postni qayta yuboring (yoki izohini tahrirlang)."
                    ),
                    reply_to_message_id=message.message_id
                )
            except Exception:
                pass
        return

    if not title:
        title = f"Kino {code}"

    existing = await db.get_movie_by_code(code)
    await db.add_movie(
        code=code,
        title=title,
        channel_message_id=message.message_id,
        added_by=message.from_user.id if message.from_user else 0
    )

    # Tasdiq xabari
    try:
        if existing:
            confirm_text = f"♻️ <code>{code}</code> kodi allaqachon mavjud edi — yangi post bilan yangilandi."
        elif is_edit:
            confirm_text = f"✅ Saqlandi (izoh tahrirlangandan so'ng)!\n🎬 Nomi: {title}\n🔗 Kod: <code>{code}</code>"
        else:
            confirm_text = f"✅ Saqlandi!\n🎬 Nomi: {title}\n🔗 Kod: <code>{code}</code>"

        await bot.send_message(
            chat_id=message.chat.id,
            text=confirm_text,
            parse_mode="HTML",
            reply_to_message_id=message.message_id
        )
    except Exception:
        pass

    # Yangi qo'shilgan (yoki yangilangan) kino - so'ragan foydalanuvchilarga xabar beramiz
    await notify_requesters(bot, title, code)


@router.channel_post(F.chat.id == STORAGE_CHANNEL_ID, F.video | F.document | F.animation)
async def on_channel_movie_post(message: Message, bot: Bot):
    """Saqlash kanaliga yangi video/fayl tashlanganda ishga tushadi."""
    await save_movie_from_channel(message, bot, is_edit=False)


@router.channel_post(F.chat.id == STORAGE_CHANNEL_ID, F.text)
async def on_channel_text_edit_hint(message: Message):
    """Kanalga faqat matn yozilsa (fayl bo'lmasa) - e'tiborsiz qoldiramiz."""
    pass


@router.edited_channel_post(F.chat.id == STORAGE_CHANNEL_ID, F.video | F.document | F.animation)
async def on_channel_movie_edited(message: Message, bot: Bot):
    """
    Admin avval faylni caption'siz yuborib, keyin izohini
    tahrirlab kod/nom qo'shsa - shu handler ushlab qoladi.
    """
    await save_movie_from_channel(message, bot, is_edit=True)
