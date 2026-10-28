import os, json, re
from groq import Groq

def call_llm(prompt, temperature=0.2, max_tokens=1600):
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")
    client = Groq(api_key=key)
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a careful document-grounded assistant. Never invent evidence. Follow requested output format exactly."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()

def answer_question(question, passages):
    if not passages:
        return {"answer": "I could not find relevant text in the uploaded PDFs. Try rephrasing the question.", "supported": False}
    evidence = "\n\n".join(
        f"[Source: {p.metadata.get('source')} | page {p.metadata.get('page')}]\n{p.page_content}"
        for p in passages
    )
    prompt = f"""Answer the question using ONLY the evidence below.
Question: {question}
Instructions:
- Cite claims using [document name, page N].
- If the evidence does not answer the question, clearly say so.
- Do not use outside knowledge as if it came from the PDFs.
- Keep the answer clear and concise.
- End with a section called "Evidence check" describing which passages support the answer and any uncertainty.
EVIDENCE:
{evidence}
"""
    answer = call_llm(prompt, temperature=0.1, max_tokens=1200)
    # Conservative heuristic: citations or explicit insufficiency are required.
    has_citation = bool(re.search(r"\[.+?,\s*page\s+\d+\]", answer, re.I))
    says_unknown = any(x in answer.lower() for x in ["not stated in the provided", "does not contain enough", "cannot determine", "not enough evidence", "could not find"])
    return {"answer": answer, "supported": has_citation or says_unknown}

def _json_from_text(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("["), text.rfind("]")
    if start >= 0 and end > start:
        text = text[start:end+1]
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def generate_quiz(passages, count=5, qtype="Mixed", difficulty="Medium"):
    evidence = "\n\n".join(
        f"[{p.metadata.get('source')} page {p.metadata.get('page')}]\n{p.page_content}"
        for p in passages
    )
    prompt = f"""Create {count} educational quiz questions using only the evidence.
Question type: {qtype}. Difficulty: {difficulty}.
Return ONLY valid JSON array. Each item must contain:
{{"type":"MCQ|True/False|Short answer","question":"...","options":["..."],"answer":"exact correct option or answer","explanation":"why it is correct, grounded in evidence","topic":"short topic name"}}
For True/False, options must be ["True","False"] and answer one of them.
For Short answer, options must be [].
Avoid ambiguous questions. Do not repeat questions. Ensure answer is supported by evidence.
EVIDENCE:
{evidence}
"""
    return _json_from_text(call_llm(prompt, temperature=0.25, max_tokens=2200))

def evaluate_short_answer(user_answer, correct_answer, explanation=""):
    if not user_answer.strip():
        return False
    prompt = f"""Decide whether the student's answer is substantially correct.
Expected answer: {correct_answer}
Student answer: {user_answer}
Explanation/context: {explanation}
Return exactly YES or NO. Be fair about paraphrases."""
    try:
        return call_llm(prompt, temperature=0, max_tokens=5).strip().upper().startswith("YES")
    except Exception:
        return user_answer.strip().lower() == correct_answer.strip().lower()

def summarize_documents(passages, style="Concise"):
    evidence = "\n\n".join(f"[{p.metadata.get('source')} page {p.metadata.get('page')}]\n{p.page_content}" for p in passages)
    return call_llm(f"""Summarize these PDF excerpts in {style} style.
Use headings and bullets. Cite important claims as [document name, page N].
Do not add facts absent from the excerpts.
EXCERPTS:
{evidence}""", max_tokens=1800)

def make_flashcards(passages, count=8):
    evidence = "\n\n".join(f"[{p.metadata.get('source')} page {p.metadata.get('page')}]\n{p.page_content}" for p in passages)
    prompt = f"""Create {count} useful study flashcards from the evidence. Return only a JSON array with objects {{"front":"question or term","back":"concise answer and citation [document, page N]"}}. Avoid duplicates.
EVIDENCE:
{evidence}"""
    return _json_from_text(call_llm(prompt, temperature=0.2, max_tokens=1800))

def build_study_plan(passages, days, hours):
    evidence = "\n\n".join(f"[{p.metadata.get('source')} page {p.metadata.get('page')}]\n{p.page_content}" for p in passages)
    return call_llm(f"""Build a practical {days}-day study plan with {hours} study hour(s) per day from these excerpts. Include daily goals, active recall, review, and a short self-test. Cite document pages when assigning topics. Do not invent chapter names.
EVIDENCE:
{evidence}""", max_tokens=1800)
