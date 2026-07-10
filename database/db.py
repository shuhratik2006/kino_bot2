import aiosqlite
import time
from config import DB_PATH


async def init_db():
    """Bot ishga tushganda barcha jadvallarni yaratadi (agar mavjud bo'lmasa)."""
    async with aiosqlite.connect(DB_PATH) as db:
        # WAL (Write-Ahead Logging) rejimi - o'qish/yozish parallel ishlashini
        # tezlashtiradi, ayniqsa bir nechta so'rov bir vaqtda kelganda foydali.
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.commit()

        # Foydalanuvchilar
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at INTEGER,
                is_premium INTEGER DEFAULT 0,
                premium_until INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                search_count INTEGER DEFAULT 0,
                daily_downloads INTEGER DEFAULT 0,
                daily_downloads_date TEXT DEFAULT ''
            )
        """)

        # Kinolar (kanalga yuklangan, kod bilan bog'langan)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                channel_message_id INTEGER NOT NULL,
                description TEXT,
                added_by INTEGER,
                added_at INTEGER,
                views INTEGER DEFAULT 0
            )
        """)

        # Majburiy obuna kanallari (dinamik - istalgan payt qo'shiladi/o'chiriladi)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS force_sub_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL UNIQUE,
                title TEXT,
                invite_link TEXT,
                added_at INTEGER
            )
        """)

        # Adminlar (bosh admin + qo'shilgan adminlar)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at INTEGER
            )
        """)

        # Foydalanuvchilar so'ragan kinolar (bazada topilmagan, TMDB orqali
        # topilib "So'rash" tugmasi bosilgan). Kino keyin qo'shilsa, shu
        # jadvaldagi foydalanuvchilarga avtomatik xabar boradi.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movie_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                query_title TEXT NOT NULL,
                query_year TEXT,
                requested_at INTEGER,
                notified INTEGER DEFAULT 0,
                is_priority INTEGER DEFAULT 0
            )
        """)

        await db.commit()

        # --- Migratsiya: eski o'rnatilgan bazalarga yangi ustunlarni qo'shish ---
        for col_def in [
            "ALTER TABLE users ADD COLUMN daily_downloads INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN daily_downloads_date TEXT DEFAULT ''",
            "ALTER TABLE movie_requests ADD COLUMN is_priority INTEGER DEFAULT 0",
        ]:
            try:
                await db.execute(col_def)
                await db.commit()
            except Exception:
                pass  # ustun allaqachon mavjud


# ---------------- USERS ----------------

async def add_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, joined_at) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, int(time.time()))
            )
            await db.commit()
            return True  # yangi foydalanuvchi
        else:
            await db.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username, full_name, user_id)
            )
            await db.commit()
            return False


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def is_premium(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user:
        return False
    if user["is_premium"] and user["premium_until"] > int(time.time()):
        return True
    return False


async def set_premium(user_id: int, days: int):
    until = int(time.time()) + days * 86400
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE user_id = ?",
            (until, user_id)
        )
        await db.commit()
    return until


async def remove_premium(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium = 0, premium_until = 0 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def ban_user(user_id: int, banned: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (int(banned), user_id))
        await db.commit()


async def is_banned(user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and user["is_banned"])


# ---------------- KUNLIK YUKLAB OLISH LIMITI ----------------

def _today_str() -> str:
    return time.strftime("%Y-%m-%d")


async def get_daily_downloads(user_id: int) -> int:
    """
    Foydalanuvchining bugungi yuklab olishlar sonini qaytaradi.
    Agar oxirgi yozuv boshqa kunga tegishli bo'lsa, avtomatik 0 deb hisoblanadi
    (bazada reset qilinmaydi, faqat increment vaqtida yangilanadi).
    """
    user = await get_user(user_id)
    if not user:
        return 0
    if user["daily_downloads_date"] != _today_str():
        return 0
    return user["daily_downloads"]


async def increment_daily_downloads(user_id: int):
    today = _today_str()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT daily_downloads, daily_downloads_date FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()

        if row and row["daily_downloads_date"] == today:
            new_count = row["daily_downloads"] + 1
        else:
            new_count = 1  # yangi kun boshlandi - hisoblagich reset

        await db.execute(
            "UPDATE users SET daily_downloads = ?, daily_downloads_date = ? WHERE user_id = ?",
            (new_count, today, user_id)
        )
        await db.commit()
        return new_count


async def increment_search_count(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET search_count = search_count + 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_banned = 0")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1 AND premium_until > ?", (int(time.time()),))
        total_premium = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM movies")
        total_movies = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE joined_at > ?", (int(time.time()) - 86400,))
        today_users = (await cur.fetchone())[0]

        return {
            "total_users": total_users,
            "total_premium": total_premium,
            "total_movies": total_movies,
            "today_users": today_users,
        }


# ---------------- MOVIES ----------------

async def add_movie(code: str, title: str, channel_message_id: int, added_by: int, description: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO movies (code, title, channel_message_id, description, added_by, added_at, views)
               VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT views FROM movies WHERE code = ?), 0))""",
            (code, title, channel_message_id, description, added_by, int(time.time()), code)
        )
        await db.commit()


async def get_movie_by_code(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM movies WHERE code = ?", (code,))
        return await cur.fetchone()


async def search_movies_by_title(query: str, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM movies WHERE title LIKE ? ORDER BY views DESC LIMIT ?",
            (f"%{query}%", limit)
        )
        return await cur.fetchall()


async def delete_movie(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM movies WHERE code = ?", (code,))
        await db.commit()
        return cur.rowcount > 0


async def increment_views(code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE movies SET views = views + 1 WHERE code = ?", (code,))
        await db.commit()


# ---------------- FORCE SUB CHANNELS ----------------

async def add_force_sub_channel(chat_id: str, title: str, invite_link: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO force_sub_channels (chat_id, title, invite_link, added_at) VALUES (?, ?, ?, ?)",
            (chat_id, title, invite_link, int(time.time()))
        )
        await db.commit()


async def remove_force_sub_channel(chat_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM force_sub_channels WHERE chat_id = ?", (chat_id,))
        await db.commit()
        return cur.rowcount > 0


async def get_force_sub_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM force_sub_channels ORDER BY added_at")
        return await cur.fetchall()


# ---------------- ADMINS ----------------

async def add_admin(user_id: int, added_by: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
            (user_id, added_by, int(time.time()))
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await db.commit()
        return cur.rowcount > 0


async def get_all_admins():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ---------------- MOVIE REQUESTS (so'rovlar) ----------------

async def add_movie_request(user_id: int, query_title: str, query_year: str = "", is_priority: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        # Bir xil foydalanuvchi bir xil nomni ikki marta so'ramasin
        cur = await db.execute(
            "SELECT id FROM movie_requests WHERE user_id = ? AND query_title = ? AND notified = 0",
            (user_id, query_title)
        )
        existing = await cur.fetchone()
        if existing:
            return False  # allaqachon so'ragan

        await db.execute(
            "INSERT INTO movie_requests (user_id, query_title, query_year, requested_at, is_priority) VALUES (?, ?, ?, ?, ?)",
            (user_id, query_title, query_year, int(time.time()), int(is_priority))
        )
        await db.commit()
        return True


async def get_user_requests(user_id: int):
    """Foydalanuvchining barcha so'rovlarini (kutilayotgan va bajarilgan) qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM movie_requests WHERE user_id = ? ORDER BY requested_at DESC",
            (user_id,)
        )
        return await cur.fetchall()


async def delete_user_request(request_id: int, user_id: int):
    """Foydalanuvchi o'z so'rovini bekor qilishi uchun (faqat o'zinikini o'chira oladi)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM movie_requests WHERE id = ? AND user_id = ?",
            (request_id, user_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def find_matching_requests(title: str):
    """
    Yangi qo'shilgan kino nomiga mos keladigan, hali xabar berilmagan
    so'rovlarni topadi. Oddiy "so'z ichida bor-yo'qligi" solishtiruvi bilan
    ishlaydi (katta-kichik harfga sezgir emas). Premium (priority)
    so'rovlar ro'yxat boshida keladi.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM movie_requests WHERE notified = 0 ORDER BY is_priority DESC, requested_at ASC"
        )
        rows = await cur.fetchall()

    title_lower = title.lower()
    matches = []
    for r in rows:
        q = r["query_title"].lower()
        if q in title_lower or title_lower in q:
            matches.append(r)
    return matches


async def get_pending_requests(limit: int = 30):
    """Admin panel uchun: barcha kutilayotgan so'rovlar, premium birinchi."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM movie_requests WHERE notified = 0 "
            "ORDER BY is_priority DESC, requested_at ASC LIMIT ?",
            (limit,)
        )
        return await cur.fetchall()


async def mark_requests_notified(request_ids: list):
    if not request_ids:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        placeholders = ",".join("?" * len(request_ids))
        await db.execute(
            f"UPDATE movie_requests SET notified = 1 WHERE id IN ({placeholders})",
            request_ids
        )
        await db.commit()


async def get_pending_requests_count():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM movie_requests WHERE notified = 0")
        return (await cur.fetchone())[0]
