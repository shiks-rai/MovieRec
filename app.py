"""
Step 3: the web app.   Run with:  streamlit run app.py
Posters come from the TMDB API, so you need a free key in TMDB_API_KEY.
"""
import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

from recommender import Recommender

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
POSTER_BASE = "https://image.tmdb.org/t/p/w342"

st.set_page_config(page_title="Movie Recommender", page_icon="🎬", layout="wide")


@st.cache_resource
def get_recommender():
    return Recommender()


@st.cache_data(show_spinner=False)
def fetch_poster(movie_id):
    """Ask TMDB for the poster of one movie. Returns a URL, or None."""
    if not TMDB_API_KEY:
        return None
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/movie/{int(movie_id)}",
            params={"api_key": TMDB_API_KEY},
            timeout=5,
        )
        r.raise_for_status()
        path = r.json().get("poster_path")
        return POSTER_BASE + path if path else None
    except requests.RequestException:
        return None


rec = get_recommender()

st.title("🎬 Movie Recommender")
st.caption("Pick a movie you like. We find movies with a similar plot, genres, cast and director.")

left, right = st.columns([3, 1])
with left:
    chosen = st.selectbox("Movie you like", rec.titles(), index=None, placeholder="Start typing a title...")
with right:
    n = st.slider("How many suggestions", 3, 10, 5)

if chosen:
    results = rec.recommend(chosen, n)
    st.subheader(f"Because you liked {chosen}")

    cols = st.columns(min(n, 5))
    for i, row in enumerate(results.itertuples()):
        with cols[i % len(cols)]:
            poster = fetch_poster(row.id)
            if poster:
                st.image(poster, use_container_width=True)
            else:
                st.markdown("🎞️ *(no poster)*")
            year = int(row.release_year) if pd.notna(row.release_year) else "?"
            st.markdown(f"**{row.title}** ({year})")
            st.caption(f"⭐ {row.vote_average:.1f}  ·  {row.similarity:.0%} match")
            st.caption(row.genres.replace(",", ", ") if row.genres else "")
            with st.expander("Plot"):
                st.write(row.overview or "No plot available.")

if not TMDB_API_KEY:
    st.info("No TMDB_API_KEY found, so posters are switched off. Recommendations still work.")

st.divider()
st.caption("This product uses the TMDB API but is not endorsed or certified by TMDB.")
