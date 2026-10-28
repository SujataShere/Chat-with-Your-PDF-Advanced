# PDF Genius AI — Advanced Chat with Your PDF

An enhanced GenAI project that combines source-grounded PDF Q&A, multi-document comparison, adaptive quizzes, learning analytics, flashcards, summaries, and study plans.

## Features

1. **Source-cited PDF Q&A** — retrieves passages using FAISS and displays source filename/page references.
2. **Evidence warning** — conservative heuristic flags answers without citations or an explicit insufficient-evidence response. This is not a formal hallucination detector.
3. **Adaptive quizzes** — generate MCQ, True/False, short-answer, or mixed quizzes at Easy/Medium/Hard difficulty.
4. **Score tracking** — saves quiz scores and attempts in a local SQLite database.
5. **Knowledge-gap analytics** — calculates topic accuracy and recommends topics below 70%.
6. **Multi-PDF comparison** — compares selected documents and asks the model to cite document/page for findings.
7. **Study tools** — summaries, flashcards, and a multi-day study plan.
8. **Chat and quiz history** — stored locally in `learning_history.db`.

## Requirements

- Python 3.10 or 3.11 recommended
- A Groq API key
- Internet access on first run to download the sentence-transformer embedding model

## Windows setup (PowerShell)

```powershell
cd path\to\Chat-with-Your-PDF-Advanced
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Put your real key in `.env`:

```env
GROQ_API_KEY=your_real_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Do not upload `.env` or share your API key on GitHub.

Run the app:

```powershell
streamlit run app.py
```

## How it works

- `pypdf` extracts text page-by-page and stores source/page metadata.
- `RecursiveCharacterTextSplitter` divides text into overlapping chunks.
- `sentence-transformers/all-MiniLM-L6-v2` creates embeddings.
- FAISS retrieves semantically relevant chunks.
- Groq-hosted LLM generates grounded answers, quizzes, summaries, and comparisons.
- SQLite stores local learning history and scores.

## Project structure

```text
Chat-with-Your-PDF-Advanced/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── learning_history.db       # created automatically; not committed
└── modules/
    ├── __init__.py
    ├── pdf_engine.py
    ├── ai_engine.py
    ├── storage.py
    └── analytics.py
```

## Important limitations

- The answer support check is heuristic. It checks for citations or an explicit uncertainty phrase; it does not prove that every claim is entailed by the cited source.
- Page citations refer to the PDF page numbering extracted by `pypdf` (1-based).
- Scanned PDFs with no text layer need OCR before upload.
- The current version keeps indexed documents in Streamlit session state; re-upload PDFs after a full app restart.
- Short-answer grading uses an LLM judgment and can be imperfect.
- This project is a learning prototype, not a high-assurance fact-verification system.

## Suggested next upgrades

- Add OCR with Tesseract for scanned documents.
- Add claim-by-claim entailment verification and citation coverage scores.
- Add per-user authentication and cloud database storage.
- Add export to PDF/CSV and a downloadable quiz report.
- Add chunk-level citations to each answer sentence.
