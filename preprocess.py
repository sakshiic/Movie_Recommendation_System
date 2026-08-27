"""
Preprocess The Movies Dataset (Kaggle) into a clean movies.csv file.

Expected raw files in data/raw/:
  - movies_metadata.csv
  - credits.csv
  - keywords.csv

Run once after downloading the dataset:
    python preprocess.py
"""

import ast
import json
import os

import numpy as np
import pandas as pd
RAW_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "movies.csv")

POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"



MIN_VOTE_COUNT = 100
MIN_VOTE_AVERAGE = 5.0
TARGET_MOVIES = 800  # keep top movies after filtering (500+ guaranteed)

def _parse_json_field(value):
    """Safely parse a JSON-like string column from the dataset."""
    if pd.isna(value) or value == "":
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value.replace("'", '"'))
    except (json.JSONDecodeError, TypeError, ValueError):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return []


def _extract_genres(genre_json):
    """Convert genre JSON to a space-separated string."""
    genres = _parse_json_field(genre_json)
    return " ".join(item["name"] for item in genres if isinstance(item, dict) and "name" in item)


def _extract_keywords(keyword_json):
    """Convert keyword JSON to a space-separated string."""
    keywords = _parse_json_field(keyword_json)
    return " ".join(item["name"] for item in keywords if isinstance(item, dict) and "name" in item)


def _extract_director(crew_json):
    """Get the director name from the crew JSON."""
    crew = _parse_json_field(crew_json)
    for person in crew:
        if isinstance(person, dict) and person.get("job") == "Director":
            return person.get("name", "")
    return ""


def _extract_cast(cast_json, top_n=3):
    """Get top N actor names from the cast JSON."""
    cast = _parse_json_field(cast_json)
    names = [person.get("name", "") for person in cast if isinstance(person, dict)]
    return " ".join(name for name in names[:top_n] if name)


def _extract_year(release_date):
    """Extract release year from a date string."""
    if pd.isna(release_date) or not str(release_date).strip():
        return np.nan
    return str(release_date)[:4]


def _check_raw_files():
    """Verify that all required raw files exist."""
    required = ["movies_metadata.csv", "credits.csv", "keywords.csv"]
    missing = [name for name in required if not os.path.exists(os.path.join(RAW_DIR, name))]
    if missing:
        raise FileNotFoundError(
            "Missing raw dataset files in data/raw/:\n"
            f"  {', '.join(missing)}\n\n"
            "Download The Movies Dataset from Kaggle:\n"
            "  https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset\n"
            "Then place movies_metadata.csv, credits.csv, and keywords.csv in data/raw/"
        )


def preprocess():
    """Load, clean, merge, and save the movie dataset."""
    _check_raw_files()
    print("Loading raw dataset files...")

    movies = pd.read_csv(os.path.join(RAW_DIR, "movies_metadata.csv"), low_memory=False)
    credits = pd.read_csv(os.path.join(RAW_DIR, "credits.csv"))
    keywords = pd.read_csv(os.path.join(RAW_DIR, "keywords.csv"))

    # Keep rows with valid numeric vote_count (also removes corrupted rows)
    movies["vote_count"] = pd.to_numeric(movies["vote_count"], errors="coerce")
    movies["vote_average"] = pd.to_numeric(movies["vote_average"], errors="coerce")
    movies = movies.dropna(subset=["vote_count", "vote_average"])

    # Use string IDs for safe merging
    movies["id"] = movies["id"].astype(str)
    credits["id"] = credits["id"].astype(str)
    keywords["id"] = keywords["id"].astype(str)

    print(f"Loaded {len(movies)} movies from metadata")
    print("\nSample poster paths:")
    print(movies["poster_path"].head(10).to_string())
    # Merge credits and keywords
    movies = movies.merge(credits[["id", "cast", "crew"]], on="id", how="left")
    movies = movies.merge(keywords[["id", "keywords"]], on="id", how="left")

    # Extract useful text fields
    movies["genres"] = movies["genres"].apply(_extract_genres)
    movies["keywords"] = movies["keywords"].apply(_extract_keywords)
    movies["director"] = movies["crew"].apply(_extract_director)
    movies["cast"] = movies["cast"].apply(_extract_cast)
    movies["year"] = movies["release_date"].apply(_extract_year)
    movies["poster_url"] = movies["poster_path"].apply(
        lambda path: f"{POSTER_BASE_URL}{path}" if pd.notna(path) and str(path).strip() else ""
    )

    # Quality filters for better recommendations
    movies = movies[
        movies["overview"].notna()
        & (movies["overview"].str.len() > 30)
        & movies["genres"].str.len().gt(0)
        & movies["poster_url"].str.len().gt(0)
        & (movies["vote_count"] >= MIN_VOTE_COUNT)
        & (movies["vote_average"] >= MIN_VOTE_AVERAGE)
        & movies["title"].notna()
    ].copy()

    # Keep the most popular/well-rated movies
    movies = movies.sort_values(["vote_count", "vote_average"], ascending=False)
    movies = movies.drop_duplicates(subset=["title"], keep="first")
    movies = movies.head(TARGET_MOVIES)

    # Final clean dataset
    clean = movies[
        ["title", "genres", "overview", "keywords", "director", "cast", "year", "vote_average", "poster_url"]
    ].copy()
    clean["year"] = pd.to_numeric(clean["year"], errors="coerce")
    clean["vote_average"] = clean["vote_average"].round(1)
    clean = clean.reset_index(drop=True)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    clean.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(clean)} movies to {OUTPUT_PATH}")
    print(f"Sample titles: {', '.join(clean['title'].head(5).tolist())}")
    return clean


if __name__ == "__main__":
    preprocess()
