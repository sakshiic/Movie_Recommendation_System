# Movie Recommendation System

A **content-based movie recommendation system** built with Python, scikit-learn, and Streamlit. Select a movie and get 5 similar recommendations using **TF-IDF**, **cosine similarity**, and a **genre overlap boost**.

Built for BTech college projects, resume portfolios, and viva interviews.

## Features

- **500+ real movies** from [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) (TMDB)
- Content-based filtering with weighted feature engineering
- TF-IDF vectorization + cosine similarity + genre boost
- Streamlit web UI with movie dropdown, posters, year, and rating
- Simple evaluation script (`Genre Overlap @5`)
- Beginner-friendly, well-commented code

## Project Structure

```
Movie_Recommendation_System/
├── app.py              # Streamlit web interface
├── recommender.py      # Recommendation engine (TF-IDF + cosine + genre boost)
├── preprocess.py       # Cleans raw Kaggle data → data/movies.csv
├── evaluate.py         # Simple recommendation quality check
├── data/
│   ├── raw/            # Place Kaggle CSV files here (not committed to git)
│   └── movies.csv      # Generated clean dataset (run preprocess.py)
├── requirements.txt
├── .gitignore
└── README.md
```

## Dataset Setup (One-Time)

### Step 1: Download from Kaggle

1. Create a free account at [kaggle.com](https://www.kaggle.com)
2. Open: [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset)
3. Click **Download** and extract the ZIP file
4. Copy these 3 files into `data/raw/`:
   - `movies_metadata.csv`
   - `credits.csv`
   - `keywords.csv`

Your folder should look like:

```
data/raw/
├── movies_metadata.csv
├── credits.csv
└── keywords.csv
```

### Step 2: Preprocess the data

```bash
python preprocess.py
```

This creates `data/movies.csv` with ~800 high-quality movies (filtered from 45,000+).

## Run the App

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start Streamlit

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## Run Evaluation

After preprocessing, check recommendation quality:

```bash
python evaluate.py
```

This reports **Genre Overlap @5** — the percentage of top-5 recommendations that share at least one genre with the selected movie.

## How It Works

### 1. Preprocessing (`preprocess.py`)

- Loads raw TMDB CSV files with **Pandas**
- Parses JSON fields (genres, keywords, cast, crew) using **NumPy/Pandas**
- Merges credits and keywords into movie metadata
- Filters movies with valid overview, poster, rating, and vote count
- Saves a clean `movies.csv`

### 2. Feature Engineering (`recommender.py`)

For each movie, these fields are combined into one text feature:

| Field | Weight |
|-------|--------|
| Genres | Repeated 3× (higher importance) |
| Keywords | 1× |
| Director | 1× |
| Top 3 cast | 1× |
| Overview | 1× |

### 3. Recommendation Algorithm

```
Final Score = 0.80 × Cosine Similarity + 0.20 × Genre Overlap (Jaccard)
```

- **TF-IDF** converts text features into numerical vectors
- **Cosine similarity** measures content closeness between movies
- **Genre boost** pushes movies with shared genres higher in the ranking

### 4. Streamlit UI (`app.py`)

- Searchable movie dropdown (800 titles with year)
- Selected movie with poster, year, rating, overview
- 5 recommendations with posters, shared genres, and match score

## Technologies Used

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Pandas | Data loading and preprocessing |
| NumPy | Numerical operations |
| scikit-learn | TF-IDF and cosine similarity |
| Streamlit | Web interface |

## For BTech Viva / Interview

**Q: What type of recommendation system is this?**  
A: Content-based filtering. It recommends movies similar in content (genres, plot, cast) to the selected movie.

**Q: Why TF-IDF?**  
A: TF-IDF converts text into numbers. Important words get higher weight; common words get lower weight.

**Q: Why cosine similarity?**  
A: It measures the angle between two movie vectors. Higher similarity = more similar content.

**Q: What is the genre boost?**  
A: After cosine similarity, we add a bonus for movies that share genres with the selected movie. This improves relevance.

**Q: Why not collaborative filtering?**  
A: Collaborative filtering needs user ratings from many users. Content-based works with movie metadata alone.

**Q: How do you evaluate quality?**  
A: We use Genre Overlap @5 — how many of the top 5 recommendations share at least one genre with the input movie.

## Resume Bullet Point

> Built a content-based movie recommendation system using TF-IDF vectorization and cosine similarity on 800+ TMDB movies, with weighted feature engineering (genres, keywords, cast, director) and a Streamlit web interface.

## Dataset Credit

- [The Movies Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) by Rounak Banik (TMDB data)
- Movie posters via [TMDB Image CDN](https://www.themoviedb.org/)

## Author

BTech Project — Movie Recommendation System
