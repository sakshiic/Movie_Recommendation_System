import streamlit as st
import requests
from io import BytesIO
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
@st.cache_data(ttl=3600, show_spinner=False)
def load_poster(url):
    """Download a poster safely and return it as an image.

    Behavior:
    - Try the provided URL first.
    - If it fails and appears to be a TMDB image URL, reconstruct the poster path and
      attempt alternative TMDB sizes (w500, w342, original) to find an available image.
    - Strictly verify HTTP status and Content-Type before attempting to open with PIL.
    """

    if not url or str(url).strip().lower() in {"", "none", "nan", "0"}:
        return None

    url = str(url).strip()
    parsed = urlparse(url)

    # Reject local/loopback hosts and other development hosts so the UI never
    # displays raw localhost/media URLs. Treat unexpected hostnames safely.
    hostname = (parsed.hostname or "").lower()
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return None

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    max_size = 10 * 1024 * 1024  # 10 MB

    def _fetch_image_from_url(u):
        try:
            resp = requests.get(u, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        except requests.RequestException:
            return None
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("Content-Type", "").lower()
        if not content_type.startswith("image/"):
            return None
        if len(resp.content) > max_size:
            return None
        try:
            img = Image.open(BytesIO(resp.content))
            img.load()
        except (UnidentifiedImageError, OSError):
            return None
        if img.mode not in {"RGB", "RGBA"}:
            img = img.convert("RGB")
        return img

    # Try the provided URL first
    image = _fetch_image_from_url(url)
    if image is not None:
        return image

    # If the URL looks like a TMDB image, try alternate sizes
    try:
        hostname = parsed.netloc.lower()
        path = parsed.path or ""
        if "image.tmdb.org" in hostname and "/t/p/" in path:
            # path like /t/p/w500/abcd.jpg -> extract the trailing poster path after the size
            tail = path.split('/t/p/', 1)[1]  # e.g. 'w500/abcd.jpg' or 'abcd.jpg'
            if '/' in tail:
                # remove size segment
                _, actual_path = tail.split('/', 1)
            else:
                actual_path = tail

            sizes = ["w500", "w342", "original"]
            for size in sizes:
                candidate = f"https://image.tmdb.org/t/p/{size}/{actual_path}"
                image = _fetch_image_from_url(candidate)
                if image is not None:
                    return image
    except Exception:
        # Any unexpected parsing error should not crash the app; fall through to None
        pass

    return None

def show_poster(url, width=300):
    """Display poster or a clean fallback when unavailable.

    If a poster image can be loaded, show it. Otherwise generate a small
    local placeholder image (PIL) and display it with st.image. This avoids
    broken image icons and does not require adding files to the repo.
    """

    image = load_poster(url)

    if image is not None:
        st.image(image, width=width)
        return

    # Create a local placeholder image (keeps UI consistent and avoids new files)
    placeholder_height = int(width * 1.4)

    # Wrap placeholder generation to ensure any unexpected PIL/font error
    # cannot crash the app. On failure fall back to a minimal solid image.
    try:
        placeholder = Image.new("RGB", (width, placeholder_height), (12, 10, 22))
        draw = ImageDraw.Draw(placeholder)

        # Dark purple / near-black cinematic background with subtle gradients.
        for y in range(placeholder_height):
            ratio = y / max(1, placeholder_height - 1)
            r = int(12 + ratio * 8)
            g = int(10 + ratio * 10)
            b = int(22 + ratio * 18)
            draw.line((0, y, width, y), fill=(r, g, b))

        # Gentle purple glow behind the icon to keep the poster premium and cinematic.
        glow = Image.new("RGBA", (width, placeholder_height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse(
            (width * 0.22, placeholder_height * 0.06, width * 0.78, placeholder_height * 0.58),
            fill=(164, 92, 210, 30),
        )
        placeholder = Image.alpha_composite(placeholder.convert("RGBA"), glow).convert("RGB")
        draw = ImageDraw.Draw(placeholder)

        # Small glowing purple/pink popcorn bucket icon in the upper-middle.
        cx = width / 2
        cy = placeholder_height * 0.29
        bucket_w = width * 0.38
        bucket_h = placeholder_height * 0.18
        left = cx - bucket_w / 2
        right = cx + bucket_w / 2
        top = cy - bucket_h / 2
        bottom = cy + bucket_h / 2

        draw.rounded_rectangle((left, top, right, bottom), radius=14, fill=(18, 16, 28), outline=(196, 116, 255), width=2)
        draw.rounded_rectangle((left + 12, top - 10, right - 12, top + 8), radius=8, fill=(42, 34, 60), outline=(255, 112, 214), width=1)

        # Popcorn kernels with purple/pink glow.
        kernel_r = max(4, width * 0.02)
        for px, py in [
            (left + 24, top + 18), (left + 48, top + 34), (left + 76, top + 16),
            (right - 24, top + 18), (right - 48, top + 34), (right - 76, top + 16),
            (cx - 16, top + 30), (cx + 16, top + 30),
        ]:
            draw.ellipse((px - kernel_r, py - kernel_r, px + kernel_r, py + kernel_r), fill=(255, 130, 220), outline=(192, 120, 255), width=1)

        # Small sparkles around the icon.
        for sx, sy in [
            (width * 0.18, placeholder_height * 0.18),
            (width * 0.82, placeholder_height * 0.18),
            (width * 0.26, placeholder_height * 0.50),
            (width * 0.74, placeholder_height * 0.50),
        ]:
            draw.line((sx - 3, sy, sx + 3, sy), fill=(255, 156, 230), width=2)
            draw.line((sx, sy - 3, sx, sy + 3), fill=(255, 156, 230), width=2)

        # Thin purple border along the poster edge.
        draw.rounded_rectangle((2, 2, width - 2, placeholder_height - 2), radius=12, outline=(120, 82, 170), width=1)

        def load_font(size):
            for candidate in ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arial.ttf"]:
                try:
                    return ImageFont.truetype(candidate, size)
                except Exception:
                    pass
            return ImageFont.load_default()

        def _measure_text(draw_obj, text, font_obj):
            try:
                bbox = draw_obj.textbbox((0, 0), text, font=font_obj)
                return bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                pass
            try:
                if font_obj is not None and hasattr(font_obj, "getbbox"):
                    bbox = font_obj.getbbox(text)
                    return bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                pass
            return (len(text) * 7, 14)

        title_font = load_font(max(18, int(width * 0.08)))
        sub_font = load_font(max(10, int(width * 0.04)))

        title = "POSTER\nUNAVAILABLE"
        subtitle = "Stay tuned for\nthe artwork"

        w_title, h_title = _measure_text(draw, "POSTER", title_font)
        w_subtitle, h_subtitle = _measure_text(draw, "UNAVAILABLE", title_font)
        w_meta, h_meta = _measure_text(draw, "Stay tuned for", sub_font)

        y_title = placeholder_height * 0.64
        y_subtitle = y_title + h_title + 4
        y_meta = y_subtitle + h_subtitle + 14

        x_title = (width - max(w_title, w_subtitle)) / 2
        x_meta = (width - w_meta) / 2

        # Purple-pink neon text with premium glow.
        for offset, color in [(0, (255, 112, 214)), (1, (181, 99, 255)), (2, (255, 156, 230))]:
            draw.text((x_title + offset, y_title + offset), "POSTER", fill=color, font=title_font)
            draw.text((x_title + offset, y_subtitle + offset), "UNAVAILABLE", fill=color, font=title_font)

        draw.text((x_title, y_title), "POSTER", fill=(255, 123, 220), font=title_font)
        draw.text((x_title, y_subtitle), "UNAVAILABLE", fill=(196, 118, 255), font=title_font)

        divider_x1 = width * 0.28
        divider_x2 = width * 0.72
        divider_y = y_subtitle + h_subtitle + 10
        draw.line((divider_x1, divider_y, divider_x2, divider_y), fill=(196, 118, 255), width=2)

        draw.text((x_meta, divider_y + 12), "Stay tuned for", fill=(211, 200, 230), font=sub_font)
        draw.text((x_meta - 10, divider_y + 12 + h_meta + 2), "the artwork", fill=(211, 200, 230), font=sub_font)

        st.image(placeholder, width=width)
        return
    except Exception:
        # As a last resort create a minimal solid placeholder and show it
        try:
            fallback = Image.new("RGB", (width, placeholder_height), (40, 40, 50))
            st.image(fallback, width=width)
            return
        except Exception:
            # If even this fails, avoid crashing the app — show nothing
            return

from recommender import (
    _title_from_select_option,
    get_all_movies_for_select,
    get_recommendations,
    load_movies,
)

# Page configuration
st.set_page_config(
    page_title="CineMatch | Movie Recommendation System",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #09090f 0%, #11111b 50%, #17121f 100%);
    }

    .block-container {
        max-width: 1250px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        padding: 35px;
        border-radius: 24px;
        background: linear-gradient(135deg, #191923, #24152f);
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 25px;
        box-shadow: 0 15px 40px rgba(0,0,0,0.35);
    }

    .hero-title {
        font-size: 46px;
        font-weight: 800;
        color: white;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        font-size: 18px;
        color: #b9b9c7;
        line-height: 1.6;
    }

    .hero-badge {
        display: inline-block;
        padding: 7px 14px;
        border-radius: 30px;
        background: rgba(139,92,246,0.15);
        color: #c4b5fd;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 15px;
    }

    .section-title {
        font-size: 27px;
        font-weight: 750;
        color: white;
        margin-top: 20px;
        margin-bottom: 15px;
    }

    .movie-card {
        background: linear-gradient(145deg, rgba(27,27,39,0.96), rgba(19,19,28,0.96));
        border: 1px solid rgba(168,85,247,0.18);
        border-radius: 18px;
        padding: 15px;
        margin-top: 8px;
        min-height: 175px;
        box-shadow: 0 12px 30px rgba(76,29,149,0.18), 0 0 0 1px rgba(96,165,250,0.06);
    }

    div[data-testid="stImage"] {
        overflow: hidden;
        border-radius: 18px;
        background: linear-gradient(135deg, rgba(168,85,247,0.12), rgba(59,130,246,0.10));
        box-shadow: 0 12px 28px rgba(15,23,42,0.38), 0 0 0 1px rgba(192,132,252,0.16);
    }

    div[data-testid="stImage"] img {
        display: block;
        width: 100%;
        height: auto;
        border-radius: 18px;
    }

    .movie-title {
        color: white;
        font-size: 16px;
        font-weight: 700;
        line-height: 1.3;
        margin-bottom: 8px;
    }

    .movie-info {
        color: #a8a8b8;
        font-size: 13px;
        line-height: 1.5;
    }

    .match-badge {
        display: inline-block;
        color: #86efac;
        background: rgba(34,197,94,0.10);
        border-radius: 20px;
        padding: 4px 9px;
        font-size: 12px;
        font-weight: 700;
        margin-top: 6px;
    }

    .selected-box {
        background: linear-gradient(145deg, rgba(28,28,40,0.96), rgba(21,21,31,0.94));
        border: 1px solid rgba(96,165,250,0.18);
        border-radius: 20px;
        padding: 22px;
        margin-top: 10px;
        box-shadow: 0 15px 35px rgba(59,130,246,0.10), 0 0 0 1px rgba(192,132,252,0.08);
    }

    .selected-title {
        color: white;
        font-size: 28px;
        font-weight: 750;
    }

    .selected-description {
        color: #b8b8c5;
        font-size: 15px;
        line-height: 1.7;
    }

    .stat-box {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 15px;
        padding: 15px;
        text-align: center;
    }

    .stat-number {
        font-size: 25px;
        font-weight: 800;
        color: white;
    }

    .stat-label {
        color: #9999a8;
        font-size: 12px;
    }

    section[data-testid="stSidebar"] {
        background: #0e0e15;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
        min-height: 45px;
    }

    div[data-baseweb="select"] > div {
        border-radius: 12px;
    }

    footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Hero section
st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">🎬 AI-POWERED MOVIE DISCOVERY</div>
        <div class="hero-title">CineMatch</div>
        <div class="hero-subtitle">
            Discover movies you'll love based on genres, keywords,
            cast and story similarity.<br>
            Powered by <b>TF-IDF + Cosine Similarity</b>.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.markdown("## 🎬 CineMatch")
    st.caption("Your personal movie discovery system")
    st.divider()

    st.markdown("### 🧠 How it works")

    st.markdown(
        """
        **1️⃣ Select a movie**

        Choose a movie from the list.

        **2️⃣ Convert text to numbers**

        TF-IDF converts movie information into numerical vectors.

        **3️⃣ Find similarity**

        Cosine similarity compares movies.

        **4️⃣ Genre boost**

        Movies sharing genres get a small preference.

        **5️⃣ Recommend**

        The system displays the top 5 similar movies.
        """
    )

    st.divider()

    try:
        movies_df = load_movies()
        st.metric("🎞️ Movies in Dataset", len(movies_df))
    except FileNotFoundError:
        movies_df = None
        st.error("Dataset not found. Run `python preprocess.py` first.")

    st.divider()
    st.caption("CONTENT-BASED FILTERING")
    st.caption("TF-IDF • COSINE SIMILARITY • GENRE BOOST")

# Load movies
try:
    movie_options = get_all_movies_for_select()

except FileNotFoundError:
    st.error(
        """
        ### Dataset not ready

        Please make sure you have:

        1. `movies_metadata.csv`
        2. `credits.csv`
        3. `keywords.csv`

        inside:

        `data/raw/`

        Then run:

        `python preprocess.py`
        """
    )
    st.stop()

# Statistics
stat1, stat2, stat3 = st.columns(3)

with stat1:
    st.markdown(
        """
        <div class="stat-box">
            <div class="stat-number">800+</div>
            <div class="stat-label">MOVIES</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with stat2:
    st.markdown(
        """
        <div class="stat-box">
            <div class="stat-number">Top 5</div>
            <div class="stat-label">RECOMMENDATIONS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with stat3:
    st.markdown(
        """
        <div class="stat-box">
            <div class="stat-number">AI</div>
            <div class="stat-label">CONTENT MATCHING</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Movie search
st.markdown(
    '<div class="section-title">🔎 Find your next movie</div>',
    unsafe_allow_html=True,
)

col_search, col_btn = st.columns([5, 1])

with col_search:
    selected_option = st.selectbox(
        "Choose a movie",
        options=[""] + movie_options,
        index=0,
        placeholder="Search for a movie...",
        label_visibility="collapsed",
    )

with col_btn:
    recommend_clicked = st.button(
        "✨ Recommend",
        type="primary",
        use_container_width=True,
    )

# Default state
if not selected_option and not recommend_clicked:
    st.info(
        "🎥 Select a movie above and click **✨ Recommend** to discover similar movies."
    )

    st.markdown(
        """
        **Popular movies to try:**

        🎬 Inception &nbsp;&nbsp;
        🦇 The Dark Knight &nbsp;&nbsp;
        🚢 Titanic &nbsp;&nbsp;
        🌌 Interstellar &nbsp;&nbsp;
        🦸 The Avengers
        """,
        unsafe_allow_html=True,
    )

# Recommendation
if recommend_clicked:

    if not selected_option:
        st.warning("Please select a movie before clicking Recommend.")

    else:
        movie_title = _title_from_select_option(selected_option)

        with st.spinner("🎬 Finding movies you'll love..."):
            matched_movie, recommendations = get_recommendations(movie_title)

        if matched_movie is None:
            st.error(
                f"Movie **'{movie_title}'** was not found. Please select another movie."
            )

        else:
            year_str = (
                f" ({matched_movie['year']})"
                if matched_movie.get("year")
                else ""
            )

            st.success(
                f"✨ Recommendations generated for **{matched_movie['title']}**{year_str}"
            )

            # Selected movie
            st.markdown(
                '<div class="section-title">🎯 Your selected movie</div>',
                unsafe_allow_html=True,
            )

            sel_col1, sel_col2 = st.columns([1.1, 3])

            with sel_col1:
                    poster_url = matched_movie.get("poster_url")
                    show_poster(poster_url, width=300)
            with sel_col2:
                rating = matched_movie.get("vote_average", "N/A")
                genres = matched_movie.get("genres", "N/A")
                overview = matched_movie.get(
                    "overview",
                    "No overview available."
                )

                st.markdown(
                    f"""
                    <div class="selected-box">
                        <div class="selected-title">
                            {matched_movie['title']}{year_str}
                        </div>
                        <br>
                        <div class="movie-info">
                            🎭 <b>Genres:</b> {genres}
                        </div>
                        <div class="movie-info">
                            ⭐ <b>Rating:</b> {rating}/10
                        </div>
                        <br>
                        <div class="selected-description">
                            {overview}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Recommendations
                        # Recommendations
            st.markdown(
                '<div class="section-title">🍿 Recommended for you</div>',
                unsafe_allow_html=True,
            )

            st.caption("Based on content similarity and shared genres")

            rec_cols = st.columns(5)

            for i, rec in enumerate(recommendations[:5]):
                with rec_cols[i]:

                    poster_url = rec.get("poster_url")
                    show_poster(poster_url, width=220)

                    rec_year = (
                        f" ({rec['year']})"
                        if rec.get("year")
                        else ""
                    )

                    rating = rec.get("vote_average", "N/A")
                    genres = rec.get("genres", "N/A")
                    match_score = rec.get("similarity_score", "N/A")

                    st.markdown(
                        f"""
                        <div class="movie-card">
                            <div class="movie-title">
                                {rec['title']}{rec_year}
                            </div>
                            <div class="movie-info">
                                ⭐ {rating}/10
                            </div>
                            <div class="movie-info">
                                🎭 {genres}
                            </div>
                            <div class="match-badge">
                                Match: {match_score}%
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown("<br>", unsafe_allow_html=True)

            st.success(
                "💡 Tip: Try another movie to get a completely new set of recommendations!"
            )