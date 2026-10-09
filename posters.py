"""
Fetches movie posters from the TMDB API.

Why this is its own file: the first version cached every failed request as
"no poster", so one network hiccup hid a poster until you restarted the app.
Here a failed request is retried and is never remembered. Only real answers
from TMDB are stored.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from dotenv import load_dotenv

load_dotenv()

POSTER_BASE = "https://image.tmdb.org/t/p/w342"

# movie_id -> poster URL, or "" when TMDB really has no poster for that movie.
# Failed requests are NOT stored here, so they get retried next time.
_cache = {}


def _fetch_one(movie_id, session):
    """Ask TMDB for one poster. Retries a few times. Returns a URL, "" (TMDB has
    no poster) or None (the request failed)."""
    api_key = os.getenv("TMDB_API_KEY")
    for attempt in range(3):
        try:
            r = session.get(
                f"https://api.themoviedb.org/3/movie/{int(movie_id)}",
                params={"api_key": api_key},
                timeout=8,
            )
            if r.status_code == 429:  # asked too fast, wait and try again
                time.sleep(1)
                continue
            r.raise_for_status()
            path = r.json().get("poster_path")
            return POSTER_BASE + path if path else ""
        except requests.RequestException:
            time.sleep(0.5 * (attempt + 1))
    return None


def get_posters(movie_ids):
    """Return {movie_id: url or None}. Fetches missing ones in parallel."""
    if not os.getenv("TMDB_API_KEY"):
        return {}
    ids = [int(i) for i in movie_ids]
    todo = [i for i in ids if i not in _cache]
    if todo:
        with requests.Session() as session, ThreadPoolExecutor(max_workers=5) as pool:
            for mid, url in zip(todo, pool.map(lambda m: _fetch_one(m, session), todo)):
                if url is not None:  # only remember real answers
                    _cache[mid] = url
    return {i: (_cache.get(i) or None) for i in ids}