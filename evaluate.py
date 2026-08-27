"""
Simple evaluation script for the recommendation system.

Measures how often the top-5 recommendations share at least one genre
with the source movie (Genre Overlap @5).

Run after preprocessing:
    python evaluate.py
"""

import random

from recommender import _parse_genres, get_recommendations, load_movies

SAMPLE_SIZE = 30
RECOMMENDATIONS = 5


def genre_overlap_at_k(source_genres, recommendations):
    """
    Check each recommendation for at least one shared genre.
    Returns the fraction of recommendations with genre overlap.
    """
    if not source_genres:
        return 0.0

    hits = 0
    for rec in recommendations:
        rec_genres = _parse_genres(rec["genres"])
        if source_genres & rec_genres:
            hits += 1
    return hits / len(recommendations) if recommendations else 0.0


def run_evaluation(sample_size=SAMPLE_SIZE):
    """Run evaluation on a random sample of movies."""
    movies = load_movies()
    sample_size = min(sample_size, len(movies))
    sample_indices = random.sample(range(len(movies)), sample_size)

    scores = []
    print(f"Evaluating {sample_size} random movies...\n")
    print(f"{'Movie':<40} {'Genre Overlap @5':>18}")
    print("-" * 60)

    for idx in sample_indices:
        title = movies.iloc[idx]["title"]
        source_genres = _parse_genres(movies.iloc[idx]["genres"])

        matched, recommendations = get_recommendations(title, num_recommendations=RECOMMENDATIONS)
        if matched is None or not recommendations:
            continue

        score = genre_overlap_at_k(source_genres, recommendations)
        scores.append(score)
        print(f"{title[:38]:<40} {score * 100:>16.1f}%")

    if not scores:
        print("No scores computed. Check that data/movies.csv exists.")
        return

    average = sum(scores) / len(scores)
    print("-" * 60)
    print(f"\nAverage Genre Overlap @5: {average * 100:.1f}%")
    print(f"Movies evaluated: {len(scores)}")
    print("\nInterpretation:")
    print("  80%+  = Good recommendation quality")
    print("  60-80% = Acceptable quality")
    print("  <60%  = May need tuning")


if __name__ == "__main__":
    run_evaluation()
