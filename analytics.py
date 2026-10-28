import json
from .storage import connect

def topic_accuracy():
    totals = {}
    with connect() as c:
        rows = c.execute("SELECT topic_results FROM quiz_attempts").fetchall()
    for row in rows:
        try:
            data = json.loads(row["topic_results"] or "{}")
            for topic, results in data.items():
                totals.setdefault(topic, []).extend(results)
        except Exception:
            continue
    return {topic: round(100 * sum(vals) / len(vals), 1) for topic, vals in totals.items() if vals}

def recommend_revision(topic_scores, threshold=70):
    return [topic for topic, score in sorted(topic_scores.items(), key=lambda x: x[1]) if score < threshold]
