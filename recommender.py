"""
Movie Recommendation System using Content-Based Filtering.

Uses TF-IDF vectorization, cosine similarity, and a genre overlap boost
to recommend similar movies.
"""

import os

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.csv")

# How much genre overlap affects the final score (0.0 to 1.0)
GENRE_BOOST_WEIGHT = 0.20


def load_movies():
    """Load the cleaned movie dataset from CSV."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"Dataset not found at {DATA_PATH}. "
            "Download the Kaggle dataset to data/raw/ and run: python preprocess.py"
        )
    return pd.read_csv(DATA_PATH)


def _fill_na(value):
    """Replace missing text values with an empty string."""
    if pd.isna(value):
        return ""
    return str(value)


def build_feature_text(row):
    """
    Combine movie information into one text feature string.

    Genres are repeated to give them more weight than the overview.
    """
    genres = _fill_na(row.get("genres"))
    overview = _fill_na(row.get("overview"))
    keywords = _fill_na(row.get("keywords"))
    director = _fill_na(row.get("director"))
    cast = _fill_na(row.get("cast"))

    # Repeat genres 3 times so they influence TF-IDF more strongly
    genre_block = " ".join([genres] * 3)

    return " ".join(part for part in [genre_block, keywords, director, cast, overview] if part)


def _parse_genres(genre_string):
    """Convert a genre string into a set of genre names."""
    if pd.isna(genre_string) or not str(genre_string).strip():
        return set()
    return set(str(genre_string).split())


def genre_overlap_score(source_genres, target_genres):
    """
    Jaccard similarity between two genre sets.

    Returns a value between 0 (no overlap) and 1 (identical genres).
    """
    if not source_genres or not target_genres:
        return 0.0
    intersection = len(source_genres & target_genres)
    union = len(source_genres | target_genres)
    return intersection / union if union else 0.0


def create_similarity_matrix(movies):
    """
    Build TF-IDF vectors from movie features, then compute cosine similarity.
    """
    movies = movies.copy()
    movies["features"] = movies.apply(build_feature_text, axis=1)

    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_df=0.85,
        min_df=1,
    )
    tfidf_matrix = tfidf.fit_transform(movies["features"])
    return cosine_similarity(tfidf_matrix, tfidf_matrix)


def find_movie_index(movies, movie_title):
    """
    Find a movie by title (case-insensitive exact match, then partial match).
    """
    movie_title = movie_title.strip().lower()

    exact_match = movies[movies["title"].str.lower() == movie_title]
    if not exact_match.empty:
        return exact_match.index[0]

    partial_match = movies[movies["title"].str.lower().str.contains(movie_title, regex=False, na=False)]
    if not partial_match.empty:
        return partial_match.index[0]

    return None


def get_all_movies_for_select():
    """
    Return a sorted list of 'Title (Year)' strings for the UI dropdown.
    """
    movies = load_movies()
    movies = movies.sort_values("title")
    options = []
    for _, row in movies.iterrows():
        year = int(row["year"]) if pd.notna(row.get("year")) else "N/A"
        options.append(f"{row['title']} ({year})")
    return options


def _title_from_select_option(option):
    """Extract the movie title from a 'Title (Year)' dropdown value."""
    if option.endswith(")") and " (" in option:
        return option.rsplit(" (", 1)[0]
    return option


def _movie_to_dict(movie_row, similarity_score=None, shared_genres=None):
    """Convert a movie row to a dictionary for the UI."""
    result = {
        "title": movie_row["title"],
        "genres": movie_row["genres"],
        "overview": movie_row["overview"],
        "poster_url": (
            str(movie_row["poster_url"])
            if pd.notna(movie_row.get("poster_url"))
            else None
        ),
        "year": int(movie_row["year"]) if pd.notna(movie_row.get("year")) else None,
        "vote_average": float(movie_row["vote_average"]) if pd.notna(movie_row.get("vote_average")) else None,
    }
    if similarity_score is not None:
        result["similarity_score"] = round(similarity_score * 100, 1)
    if shared_genres is not None:
        result["shared_genres"] = shared_genres
    return result


# Cache loaded data so we don't rebuild the matrix on every search
_movies_cache = None
_similarity_cache = None


def _get_model():
    """Load movies and similarity matrix once, then reuse them."""
    global _movies_cache, _similarity_cache
    if _movies_cache is None:
        _movies_cache = load_movies()
        _similarity_cache = create_similarity_matrix(_movies_cache)
    return _movies_cache, _similarity_cache


def get_recommendations(movie_title, num_recommendations=5):
    """
    Return similar movies for the given title.

    Final score = (1 - GENRE_BOOST_WEIGHT) * cosine_similarity
                  + GENRE_BOOST_WEIGHT * genre_overlap
    """
    movies, cosine_matrix = _get_model()
    movie_index = find_movie_index(movies, movie_title)

    if movie_index is None:
        return None, []

    source_genres = _parse_genres(movies.iloc[movie_index]["genres"])
    cosine_scores = cosine_matrix[movie_index]

    # Combine cosine similarity with genre overlap boost
    combined_scores = []
    for idx, cosine_score in enumerate(cosine_scores):
        if idx == movie_index:
            continue
        target_genres = _parse_genres(movies.iloc[idx]["genres"])
        genre_score = genre_overlap_score(source_genres, target_genres)
        final_score = ((1 - GENRE_BOOST_WEIGHT) * cosine_score) + (GENRE_BOOST_WEIGHT * genre_score)
        shared = sorted(source_genres & target_genres)
        combined_scores.append((idx, final_score, shared))

    combined_scores.sort(key=lambda item: item[1], reverse=True)
    top_matches = combined_scores[:num_recommendations]

    matched_movie = _movie_to_dict(movies.iloc[movie_index])

    recommendations = []
    for idx, score, shared in top_matches:
        rec = _movie_to_dict(movies.iloc[idx], similarity_score=score, shared_genres=shared)
        recommendations.append(rec)

    return matched_movie, recommendations
