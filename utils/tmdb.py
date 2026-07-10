import aiohttp
from config import TMDB_API_KEY, TMDB_ENABLED

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w200"


async def search_tmdb(query: str, limit: int = 5):
    """
    TMDB'dan nom bo'yicha qidiradi. Faqat TAKLIF sifatida ishlatiladi —
    hech qanday fayl yoki video qaytarmaydi, faqat nom/yil/poster ma'lumoti.
    TMDB_API_KEY sozlanmagan bo'lsa, bo'sh ro'yxat qaytaradi.
    """
    if not TMDB_ENABLED:
        return []

    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "ru-RU",  # o'zbekcha yo'q, rus tili ko'proq mos nomlarni beradi
        "include_adult": "false",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(TMDB_SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
    except Exception:
        return []

    results = data.get("results", [])[:limit]
    movies = []
    for r in results:
        year = (r.get("release_date") or "")[:4]
        movies.append({
            "title": r.get("title") or r.get("original_title") or "Noma'lum",
            "year": year,
            "overview": (r.get("overview") or "")[:150],
            "poster_path": r.get("poster_path"),
        })
    return movies
