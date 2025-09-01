import os, json, re
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import requests
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/sdg_app")
engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_QG_MODEL = os.getenv("HF_QG_MODEL", "iarfmoose/t5-base-question-generator")
HF_SENTIMENT_MODEL = os.getenv("HF_SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------------- Helpers ----------------
def db_exec(sql, params=None):
    with engine.begin() as conn:
        if params is None:
            return conn.execute(text(sql))
        return conn.execute(text(sql), params)

def hf_infer(model: str, payload: dict):
    if not HF_API_TOKEN:
        raise RuntimeError("Missing HF_API_TOKEN in .env")
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def openai_generate(prompt: str) -> str:
    if not OPENAI_API_KEY:
        # Fallback basic suggestion if no key is provided
        return "Try a balanced meal: ugali with sukuma wiki and grilled tilapia; add fruits like mango or banana for dessert."
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful nutrition assistant for Kenyan households."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    resp = r.json()
    return resp["choices"][0]["message"]["content"].strip()

# ---------------- Routes ----------------
@app.route("/")
def home():
    return render_template("index.html")

# 1) AI Study Buddy (Education)
@app.route("/study-buddy", methods=["GET", "POST"])
def study_buddy():
    if request.method == "POST":
        notes = request.form.get("notes", "").strip()
        if not notes:
            flash("Please paste some study notes.", "error")
            return redirect(url_for("study_buddy"))

        # Generate questions & did-you-knows via Hugging Face
        # We'll prompt a question-generation model to return JSON.
        prompt = (
            "Generate exactly 4 quiz questions with short answers and exactly 2 'Did you know?' facts "
            "from the following study notes. Return JSON with keys 'quizzes' (list of {question, answer}) "
            "and 'facts' (list of strings). Notes:\n" + notes
        )
        try:
            # Using text-generation style by sending inputs
            out = hf_infer(HF_QG_MODEL, {"inputs": prompt, "parameters": {"max_new_tokens": 256}})
            # Models often return a list of dicts with 'generated_text'
            if isinstance(out, list) and out and "generated_text" in out[0]:
                gen_text = out[0]["generated_text"]
            elif isinstance(out, dict) and "generated_text" in out:
                gen_text = out["generated_text"]
            else:
                # fallback to stringify
                gen_text = json.dumps(out)

            # Try to extract JSON
            match = re.search(r"\{[\s\S]*\}", gen_text)
            if not match:
                raise ValueError("Model did not return JSON. Raw: " + gen_text[:500])
            data = json.loads(match.group(0))
            quizzes = data.get("quizzes", [])[:4]
            facts = data.get("facts", [])[:2]

            # Save to DB
            db_exec("INSERT INTO flashcards (source_text, question, answer) VALUES (:s, :q, :a)",
                    [{"s": notes, "q": q.get("question",""), "a": q.get("answer","")} for q in quizzes])
            db_exec("INSERT INTO did_you_know (fact) VALUES (:f)", [{"f": f} for f in facts])
            db_exec("INSERT INTO quizzes (question, correct_answer) VALUES (:q, :a)",
                    [{"q": q.get("question",""), "a": q.get("answer","")} for q in quizzes])

            return render_template("study_buddy.html", generated=True, quizzes=quizzes, facts=facts, notes=notes)
        except Exception as e:
            flash(f"Generation failed: {e}", "error")
            return redirect(url_for("study_buddy"))

    return render_template("study_buddy.html", generated=False)

# 2) Emotion Tracker (Health)
@app.route("/emotion-tracker", methods=["GET", "POST"])
def emotion_tracker():
    if request.method == "POST":
        entry = request.form.get("entry", "").strip()
        if not entry:
            flash("Please write something about your day.", "error")
            return redirect(url_for("emotion_tracker"))
        try:
            res = hf_infer(HF_SENTIMENT_MODEL, {"inputs": entry})
            # Expected: list of dicts with label/score OR nested
            label = "NEUTRAL"
            pos = 0.0
            neg = 0.0
            if isinstance(res, list):
                # take the highest
                best = max(res, key=lambda x: x.get("score", 0))
                label = best.get("label", "NEUTRAL")
                # crude mapping
                if label.upper() == "POSITIVE":
                    pos = best.get("score", 0.0)
                    neg = 1 - pos
                elif label.upper() == "NEGATIVE":
                    neg = best.get("score", 0.0)
                    pos = 1 - neg
            elif isinstance(res, dict) and "labels" in res:
                # very model-dependent; keep simple
                pass

            db_exec(
                "INSERT INTO emotion_entries (entry_text, score_positive, score_negative, label) "
                "VALUES (:t, :p, :n, :l)",
                {"t": entry, "p": float(pos), "n": float(neg), "l": label}
            )
            flash("Entry saved and analyzed.", "success")
            return redirect(url_for("emotion_tracker"))
        except Exception as e:
            flash(f"Sentiment failed: {e}", "error")
            return redirect(url_for("emotion_tracker"))

    # fetch recent entries
    rows = db_exec("SELECT id, entry_text, score_positive, score_negative, label, created_at FROM emotion_entries ORDER BY created_at ASC").fetchall()
    labels = [r.created_at.strftime("%Y-%m-%d") for r in rows]
    scores = [float(r.score_positive) - float(r.score_negative) for r in rows]  # simple mood index
    return render_template("emotion_tracker.html", labels=json.dumps(labels), scores=json.dumps(scores))

# 3) Recipe Recommender (Food)
@app.route("/recipes", methods=["GET", "POST"])
def recipes():
    suggestion = None
    if request.method == "POST":
        user_input = request.form.get("ingredients", "").strip()
        if not user_input:
            flash("Please enter ingredients or a goal.", "error")
            return redirect(url_for("recipes"))
        prompt = (
            "Suggest 3 healthy, budget-friendly Kenyan recipes based on these ingredients or goals. "
            "Return bullet points with title and short method. Ingredients/goals: "
            f"{user_input}"
        )
        try:
            suggestion = openai_generate(prompt)
            db_exec("INSERT INTO recipes (user_input, suggestion) VALUES (:u, :s)", {"u": user_input, "s": suggestion})
        except Exception as e:
            flash(f"Suggestion failed: {e}", "error")
            return redirect(url_for("recipes"))
    return render_template("recipes.html", suggestion=suggestion)

@app.route("/api/emotions")
def api_emotions():
    rows = db_exec("SELECT created_at, score_positive, score_negative FROM emotion_entries ORDER BY created_at ASC").fetchall()
    data = {
        "labels": [r.created_at.strftime("%Y-%m-%d") for r in rows],
        "scores": [float(r.score_positive) - float(r.score_negative) for r in rows]
    }
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
