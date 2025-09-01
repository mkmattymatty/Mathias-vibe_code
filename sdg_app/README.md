# SDG Trio App (Education · Health · Food)

A simple Flask + MySQL project featuring:
1) **AI Study Buddy** — generates flashcards (4 quizzes + 2 did-you-knows) via Hugging Face.
2) **Emotion Tracker** — logs journal entries and computes sentiment via Hugging Face; shows trend with Chart.js.
3) **Recipe Recommender** — suggests meals via an OpenAI-compatible text API.

## Tech
- Frontend: HTML5 + CSS (animations) + JS (flip cards, Chart.js)
- Backend: Python (Flask) + MySQL (via SQLAlchemy / PyMySQL)
- AI: Hugging Face Inference API (question generation + sentiment), OpenAI-compatible API for recipes

## Setup

1. **Clone & enter the folder**
```bash
cd sdg_app
```

2. **Create and fill your `.env`**
```bash
cp .env.example .env
# edit it to set DATABASE_URL, HF_API_TOKEN, OPENAI_API_KEY (optional), etc.
```

3. **Create MySQL DB and tables**
```sql
CREATE DATABASE sdg_app CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Then load schema.sql within that DB
```

4. **Install dependencies (use a venv recommended)**
```bash
pip install -r requirements.txt
```

5. **Run the app**
```bash
python app.py
```
Open http://127.0.0.1:5000

## Notes
- For **Study Buddy**, we call a Hugging Face model for question generation. We prompt it to return strict JSON, then parse it.
- For **Emotion Tracker**, we use `distilbert-base-uncased-finetuned-sst-2-english`. We store positive/negative scores and render a simple mood index.
- For **Recipe Recommender**, if `OPENAI_API_KEY` is missing, we return a sensible local fallback string.
- The flip cards include a timer that alerts: “Don't slumber! Hey!” if you don’t flip within 120s.

## Change Models
- Edit `.env`:
  - `HF_QG_MODEL` for question generation.
  - `HF_SENTIMENT_MODEL` for sentiment.
  - `OPENAI_MODEL` for recipe suggestions.
