"""
Movie Recommender web app.   Run with:  streamlit run app.py
Posters come from the TMDB API (free key in TMDB_API_KEY). Without a key the
app still works, it just shows lettered placeholders instead of posters.
"""
import html
import os
import random

import pandas as pd
import streamlit as st

from posters import get_posters
from recommender import Recommender

st.set_page_config(page_title="Movie Recommender", page_icon="🎟️", layout="wide")

STARTERS = ["Inception", "The Dark Knight", "Avatar", "Toy Story", "Interstellar", "The Godfather"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Limelight&family=DM+Sans:wght@400;500;700&display=swap');
:root{--velvet:#2a0f1b;--velvet2:#3b1626;--gold:#e9b44c;--cream:#f4ead9;--muted:#b9a493;--ink:#1d0b13;}
html,body,.stApp,.stMarkdown,button,input{font-family:'DM Sans',sans-serif;}
.stApp{background:radial-gradient(ellipse 90% 45% at 50% -8%,#6a2a42 0%,#2a0f1b 62%);}
#MainMenu,footer,header[data-testid="stHeader"]{visibility:hidden;height:0;}
.block-container{max-width:1100px;padding-top:2.2rem;padding-bottom:3rem;}

.title{font-family:'Limelight',serif;font-size:clamp(2.4rem,6vw,4.2rem);line-height:1;color:var(--gold);margin:0;letter-spacing:.01em;}
.lede{color:var(--muted);font-size:1.05rem;margin:.7rem 0 1.6rem;max-width:56ch;}

.stButton>button{background:transparent;color:var(--gold);border:1px solid var(--gold);border-radius:999px;padding:.35rem 1.1rem;transition:background .15s,color .15s;}
.stButton>button:hover,.stButton>button:focus-visible{background:var(--gold);color:var(--ink);border-color:var(--gold);}
div[data-baseweb="select"]>div{background:var(--velvet2);border-color:#6a3550;}

.section{font-family:'Limelight',serif;font-size:1.5rem;color:var(--cream);margin:2.4rem 0 1rem;}
.hint{color:var(--muted);margin:1.6rem 0 .6rem;}

/* ticket stub: the one memorable element */
.ticket{display:flex;background:var(--cream);color:var(--ink);border-radius:10px;overflow:hidden;box-shadow:0 22px 50px rgba(0,0,0,.5);margin-top:.4rem;}
.t-poster{flex:0 0 250px;background:var(--velvet2);}
.t-poster img{width:100%;height:100%;object-fit:cover;display:block;}
.t-body{flex:1;padding:1.6rem 1.8rem;min-width:0;}
.t-body h2{font-family:'Limelight',serif;font-weight:400;font-size:clamp(1.6rem,3.4vw,2.4rem);line-height:1.05;margin:0 0 .6rem;color:var(--ink);}
.facts{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.8rem;}
.fact{background:var(--ink);color:var(--cream);border-radius:4px;padding:.15rem .6rem;font-size:.85rem;font-weight:500;}
.chip{border:1px solid rgba(29,11,19,.45);border-radius:999px;padding:.1rem .7rem;font-size:.82rem;}
.t-plot{margin:.4rem 0 0;line-height:1.55;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;max-width:62ch;}
.t-stub{position:relative;flex:0 0 150px;border-left:2px dashed rgba(29,11,19,.4);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:1rem;}
.t-stub::before,.t-stub::after{content:"";position:absolute;left:-12px;width:22px;height:22px;border-radius:50%;background:var(--velvet);}
.t-stub::before{top:-11px;}.t-stub::after{bottom:-11px;}
.pct{font-family:'Limelight',serif;font-size:2.8rem;line-height:1;}
.pct-l{font-size:.9rem;margin-top:.2rem;font-weight:500;}

/* poster wall */
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:26px 18px;}
.p{aspect-ratio:2/3;border-radius:4px;overflow:hidden;background:var(--velvet2);box-shadow:0 12px 26px rgba(0,0,0,.5);}
.p img{width:100%;height:100%;object-fit:cover;display:block;}
.ph{display:grid;place-items:center;height:100%;font-family:'Limelight',serif;font-size:3.4rem;color:var(--gold);}
.m-title{font-weight:700;color:var(--cream);margin:.65rem 0 .1rem;line-height:1.25;}
.m-sub{color:var(--muted);font-size:.86rem;}
.bar{height:4px;border-radius:2px;background:rgba(244,234,217,.16);margin:.55rem 0 .15rem;}
.bar i{display:block;height:100%;border-radius:2px;background:var(--gold);}
.m-match{font-size:.82rem;color:var(--gold);font-weight:500;}
details{margin-top:.4rem;color:var(--muted);font-size:.88rem;}
summary{cursor:pointer;color:var(--gold);}
details p{margin:.4rem 0 0;line-height:1.5;}

@media (max-width:760px){
 .ticket{flex-direction:column;}
 .t-poster{flex:none;max-height:360px;}
 .t-stub{border-left:0;border-top:2px dashed rgba(29,11,19,.4);flex-direction:row;gap:.8rem;}
 .t-stub::before,.t-stub::after{display:none;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def get_recommender():
    return Recommender()


rec = get_recommender()
titles = rec.titles()


def pick(title):
    st.session_state["movie"] = title


def surprise():
    st.session_state["movie"] = random.choice(titles)


def poster_html(url, title):
    if url:
        return f'<img src="{html.escape(url)}" alt="Poster for {html.escape(title)}" loading="lazy">'
    return f'<div class="ph">{html.escape(title[:1].upper())}</div>'


def year_of(v):
    return int(v) if pd.notna(v) else "n/a"


def genre_chips(genres, limit=4):
    items = [g for g in (genres or "").split(",") if g][:limit]
    return "".join(f'<span class="chip">{html.escape(g)}</span>' for g in items)


def ticket(r, url):
    pct = round(r.similarity * 100)
    return (
        '<div class="ticket">'
        f'<div class="t-poster">{poster_html(url, r.title)}</div>'
        '<div class="t-body">'
        f'<h2>{html.escape(r.title)}</h2>'
        f'<div class="facts"><span class="fact">{year_of(r.release_year)}</span>'
        f'<span class="fact">Rated {r.vote_average:.1f} / 10</span>{genre_chips(r.genres)}</div>'
        f'<p class="t-plot">{html.escape(r.overview or "No plot available.")}</p>'
        '</div>'
        f'<div class="t-stub"><div class="pct">{pct}%</div><div class="pct-l">match</div></div>'
        '</div>'
    )


def wall_item(r, url):
    pct = round(r.similarity * 100)
    return (
        '<div>'
        f'<div class="p">{poster_html(url, r.title)}</div>'
        f'<div class="m-title">{html.escape(r.title)}</div>'
        f'<div class="m-sub">{year_of(r.release_year)}, rated {r.vote_average:.1f}</div>'
        f'<div class="bar"><i style="width:{pct}%"></i></div>'
        f'<div class="m-match">{pct}% match</div>'
        f'<details><summary>Plot</summary><p>{html.escape(r.overview or "No plot available.")}</p></details>'
        '</div>'
    )


# ---------- header ----------
st.markdown('<h1 class="title">Movie Recommender</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="lede">Pick a movie you love and get a few more with a similar story, '
    "feel, cast and director.</p>",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns([5, 2, 1.6], vertical_alignment="bottom")
with c1:
    chosen = st.selectbox(
        "Movie you like", titles, index=None, key="movie",
        placeholder="Search for a title...",
    )
with c2:
    n = st.slider("How many suggestions", 3, 10, 6)
with c3:
    st.button("Surprise me", on_click=surprise, use_container_width=True)

# ---------- results ----------
results = rec.recommend(chosen, n) if chosen else None

if results is None:
    st.markdown('<p class="hint">Not sure where to start? Try one of these.</p>', unsafe_allow_html=True)
    starters = [t for t in STARTERS if t in set(titles)]
    cols = st.columns(len(starters) or 1)
    for col, t in zip(cols, starters):
        col.button(t, key=f"start_{t}", on_click=pick, args=(t,), use_container_width=True)
else:
    urls = get_posters(results["id"].tolist())
    rows = list(results.itertuples())

    st.markdown(f'<div class="section">If you liked {html.escape(chosen)}</div>', unsafe_allow_html=True)
    st.markdown(ticket(rows[0], urls.get(int(rows[0].id))), unsafe_allow_html=True)

    if len(rows) > 1:
        st.markdown('<div class="section">Also worth watching</div>', unsafe_allow_html=True)
        wall = "".join(wall_item(r, urls.get(int(r.id))) for r in rows[1:])
        st.markdown(f'<div class="wall">{wall}</div>', unsafe_allow_html=True)

if not os.getenv("TMDB_API_KEY"):
    st.caption("Posters are off because no TMDB_API_KEY was found. Recommendations still work.")

st.markdown("---")
st.caption("This product uses the TMDB API but is not endorsed or certified by TMDB.")
