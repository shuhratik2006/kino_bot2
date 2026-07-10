import os
from dotenv import load_dotenv

load_dotenv()

# --- Asosiy sozlamalar ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Bosh adminning Telegram ID raqami (birinchi admin, .env orqali beriladi)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# Kino fayllari saqlanadigan shaxsiy kanal (bot shu kanalning admini bo'lishi shart)
# Format: -100xxxxxxxxxx (kanal ID raqami)
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "0"))

# Ma'lumotlar bazasi fayli
DB_PATH = os.getenv("DB_PATH", "database/bot.db")

# Nom bo'yicha qidiruvda oddiy (pullik bo'lmagan) foydalanuvchiga
# ko'rsatiladigan natijalar soni (qolganini ko'rish uchun premium kerak bo'ladi)
FREE_SEARCH_LIMIT = int(os.getenv("FREE_SEARCH_LIMIT", "3"))

# Oddiy foydalanuvchi kuniga nechta kino kodi orqali kino olishi mumkin
# (premium foydalanuvchi uchun bu cheklov qo'llanilmaydi - cheksiz)
FREE_DAILY_DOWNLOAD_LIMIT = int(os.getenv("FREE_DAILY_DOWNLOAD_LIMIT", "5"))

# Premium narxi va davomiyligi (broadcast/admin panelda ko'rsatish uchun, to'lov integratsiyasi alohida)
PREMIUM_PRICE_TEXT = os.getenv("PREMIUM_PRICE_TEXT", "1 oy - 15,000 so'm")

# Premium sotib olish va yordam uchun murojaat qilinadigan admin/kanal username'i
# (@ belgisisiz yozing, masalan: kinochimande)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "kinochimande")

# --- TMDB (The Movie Database) integratsiyasi ---
# Bazangizda kino topilmasa, tashqi manbadan taklif ko'rsatish uchun ishlatiladi.
# Bepul API kalitini shu yerdan oling: https://www.themoviedb.org/settings/api
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_ENABLED = bool(TMDB_API_KEY)
