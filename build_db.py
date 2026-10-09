"""
Step 1: turn the two TMDB CSV files into a small SQLite database.

Run once:  python build_db.py
Needs tmdb_5000_movies.csv and tmdb_5000_credits.csv in this folder.
"""
import json
import sqlite3

import pandas as pd

MOVIES_CSV = "tmdb_5000_movies.csv"
CREDITS_CSV = "tmdb_5000_credits.csv"
DB_PATH = "movies.db"


def parse(cell):
    """The CSV stores lists as JSON text, e.g. '[{"id": 28, "name": "Action"}]'.
    Turn that text into a real Python list. Bad or empty cells become []."""
    try:
        return json.loads(cell)
    except (TypeError, ValueError):
        return []


SCHEMA = """
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS keywords;
DROP TABLE IF EXISTS cast_members;
DROP TABLE IF EXISTS directors;

CREATE TABLE movies (
    id           INTEGER PRIMARY KEY,
    title        TEXT NOT NULL,
    overview     TEXT,
    release_year INTEGER,
    vote_average REAL,
    vote_count   INTEGER,
    popularity   REAL
);
CREATE TABLE genres       (movie_id INTEGER, genre   TEXT, FOREIGN KEY (movie_id) REFERENCES movies(id));
CREATE TABLE keywords     (movie_id INTEGER, keyword TEXT, FOREIGN KEY (movie_id) REFERENCES movies(id));
CREATE TABLE cast_members (movie_id INTEGER, name    TEXT, FOREIGN KEY (movie_id) REFERENCES movies(id));
CREATE TABLE directors    (movie_id INTEGER, name    TEXT, FOREIGN KEY (movie_id) REFERENCES movies(id));

CREATE INDEX idx_genres_movie   ON genres(movie_id);
CREATE INDEX idx_keywords_movie ON keywords(movie_id);
CREATE INDEX idx_cast_movie     ON cast_members(movie_id);
CREATE INDEX idx_dir_movie      ON directors(movie_id);
"""


def main():
    movies = pd.read_csv(MOVIES_CSV)
    # Keep only what we need from the credits file. Both files have a 'title'
    # column, so leaving it out here avoids a clash when merging.
    credits = pd.read_csv(CREDITS_CSV)[["movie_id", "cast", "crew"]]
    df = movies.merge(credits, left_on="id", right_on="movie_id")

    df["overview"] = df["overview"].fillna("")
    df["release_year"] = pd.to_datetime(df["release_date"], errors="coerce").dt.year

    movie_rows, genre_rows, keyword_rows, cast_rows, director_rows = [], [], [], [], []

    for row in df.itertuples():
        mid = int(row.id)
        year = None if pd.isna(row.release_year) else int(row.release_year)
        movie_rows.append((mid, row.title, row.overview, year,
                           float(row.vote_average), int(row.vote_count), float(row.popularity)))

        genre_rows += [(mid, g["name"]) for g in parse(row.genres)]
        keyword_rows += [(mid, k["name"]) for k in parse(row.keywords)]
        # The cast list is already in billing order, so the first 3 are the leads.
        cast_rows += [(mid, c["name"]) for c in parse(row.cast)[:3]]
        director_rows += [(mid, c["name"]) for c in parse(row.crew) if c.get("job") == "Director"]

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO movies VALUES (?,?,?,?,?,?,?)", movie_rows)
        conn.executemany("INSERT INTO genres VALUES (?,?)", genre_rows)
        conn.executemany("INSERT INTO keywords VALUES (?,?)", keyword_rows)
        conn.executemany("INSERT INTO cast_members VALUES (?,?)", cast_rows)
        conn.executemany("INSERT INTO directors VALUES (?,?)", director_rows)

    print(f"Built {DB_PATH}: {len(movie_rows)} movies, {len(genre_rows)} genre rows, "
          f"{len(keyword_rows)} keyword rows, {len(cast_rows)} cast rows, {len(director_rows)} director rows")


if __name__ == "__main__":
    main()
