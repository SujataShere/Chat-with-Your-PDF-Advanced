import sqlite3, json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "learning_history.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            score_pct REAL NOT NULL,
            total_questions INTEGER NOT NULL,
            difficulty TEXT,
            topic_results TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT
        )""")

def save_quiz_attempt(score_pct, total, difficulty, topic_results):
    with connect() as c:
        c.execute("INSERT INTO quiz_attempts(created_at,score_pct,total_questions,difficulty,topic_results) VALUES(?,?,?,?,?)",
                  (datetime.now().isoformat(timespec="seconds"), score_pct, total, difficulty, json.dumps(topic_results)))

def get_quiz_history(limit=20):
    with connect() as c:
        rows = c.execute("SELECT * FROM quiz_attempts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"created_at": r["created_at"], "score_pct": r["score_pct"], "total_questions": r["total_questions"], "difficulty": r["difficulty"]} for r in rows]

def save_chat(question, answer, sources):
    with connect() as c:
        c.execute("INSERT INTO chat_history(created_at,question,answer,sources) VALUES(?,?,?,?)",
                  (datetime.now().isoformat(timespec="seconds"), question, answer, json.dumps(sources)))

def get_chat_history(limit=20):
    with connect() as c:
        rows = c.execute("SELECT * FROM chat_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"created_at": r["created_at"], "question": r["question"], "answer": r["answer"], "sources": r["sources"]} for r in rows]
