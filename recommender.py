"""
Step 2: the recommendation logic.

Every movie gets a text "profile" made of its plot, genres, keywords, lead cast
and director. We turn each profile into numbers (TF-IDF) and measure how close
two movies are with cosine similarity. The closest movies are the recommendations.

Try it in the terminal:  python recommender.py "The Dark Knight"
"""
import sqlite3
import sys

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

DB_PATH = "movies.db"

# How many times each part is repeated in a movie's profile. A higher number
# means that part matters more when comparing movies. Change these, rerun a few
# movies you know, and see how the results move.
WEIGHTS = {"genres": 3, "keywords": 2, "cast": 1, "directors": 1}

# One row per movie. The sub-queries collect each movie's genres, keywords,
# cast and director from their own tables into a single comma-separated string.
QUERY = """
SELECT
    m.id, m.title, m.overview, m.release_year, m.vote_average,
    (SELECT GROUP_CONCAT(genre,   ',') FROM genres       WHERE movie_id = m.id) AS genres,
    (SELECT GROUP_CONCAT(keyword, ',') FROM keywords     WHERE movie_id = m.id) AS keywords,
    (SELECT GROUP_CONCAT(name,    ',') FROM cast_members WHERE movie_id = m.id) AS cast_names,
    (SELECT GROUP_CONCAT(name,    ',') FROM directors    WHERE movie_id = m.id) AS directors
FROM movies m
"""


def squash(csv_text):
    """'Science Fiction,Action' -> 'ScienceFiction Action'
    Removing spaces inside each item makes a name like 'Tom Hanks' one single
    token, so two movies only match on it if it is really the same person."""
    if not csv_text:
        return ""
    return " ".join(item.replace(" ", "") for item in csv_text.split(","))


def load_movies(db_path=DB_PATH):
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(QUERY, conn)

        df = df.drop_duplicates(subset="title").reset_index(drop=True)
        text_cols = ["overview", "genres", "keywords", "cast_names", "directors"]
        df[text_cols] = df[text_cols].fillna("")

    # Repeating a part makes it count for more than single plot words.
    # The numbers come from WEIGHTS at the top of this file.
    df["profile"] = (
        df["overview"] + " "
        + (df["genres"].map(squash) + " ") * WEIGHTS["genres"]
        + (df["keywords"].map(squash) + " ") * WEIGHTS["keywords"]
        + (df["cast_names"].map(squash) + " ") * WEIGHTS["cast"]
        + (df["directors"].map(squash) + " ") * WEIGHTS["directors"]
    )
    return df


class Recommender:
    def __init__(self, db_path=DB_PATH):
        self.movies = load_movies(db_path)
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
        self.matrix = self.vectorizer.fit_transform(self.movies["profile"])

    def titles(self):
        return self.movies["title"].tolist()

    def find(self, query):
        """Return the row position of the best title match, or None."""
        q = query.strip().lower()
        lower = self.movies["title"].str.lower()
        exact = lower[lower == q]
        if not exact.empty:
            return int(exact.index[0])
        partial = lower[lower.str.contains(q, regex=False)]
        return int(partial.index[0]) if not partial.empty else None

    def recommend(self, title, n=5):
        idx = self.find(title)
        if idx is None:
            return None
        # similarity of this movie to every other movie (a number from 0 to 1)
        scores = linear_kernel(self.matrix[idx], self.matrix).ravel()
        best = [i for i in scores.argsort()[::-1] if i != idx][:n]
        out = self.movies.iloc[best][
            ["id", "title", "release_year", "vote_average", "genres", "overview"]
        ].copy()
        out["similarity"] = scores[best]
        return out.reset_index(drop=True)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "The Dark Knight"
    rec = Recommender()
    result = rec.recommend(query)
    if result is None:
        print(f"No movie found matching '{query}'")
    else:
        print(f"Because you liked '{rec.movies.iloc[rec.find(query)]['title']}':\n")
        for r in result.itertuples():
            print(f"  {r.title} ({int(r.release_year) if pd.notna(r.release_year) else '?'})"
                  f"  rating {r.vote_average}  similarity {r.similarity:.2f}")
