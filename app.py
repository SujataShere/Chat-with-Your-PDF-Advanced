import os
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from modules.pdf_engine import process_pdfs, retrieve_context, compare_documents
from modules.ai_engine import answer_question, generate_quiz, evaluate_short_answer, summarize_documents, make_flashcards, build_study_plan
from modules.storage import (
    init_db,
    save_quiz_attempt,
    get_quiz_history,
    save_chat,
    get_chat_history
)
from modules.analytics import topic_accuracy, recommend_revision

load_dotenv()
st.set_page_config(page_title="PDF Genius AI", page_icon="📚", layout="wide")
init_db()

st.title("📚 PDF Genius AI")
st.caption("Source-grounded PDF research, adaptive quizzes, and personalized learning")

with st.sidebar:
    st.header("⚙️ Setup")
    api_key_present = bool(os.getenv("GROQ_API_KEY"))
    if api_key_present:
        st.success("Groq API key detected")
    else:
        st.warning("Add GROQ_API_KEY to your .env file to enable AI features.")
    st.markdown("**Features**")
    st.markdown("- Source citations & evidence checks\n- Adaptive quizzes & score tracking\n- Multi-PDF comparison\n- Knowledge-gap analytics\n- Summaries, flashcards & study plans")

uploads = st.file_uploader("Upload one or more PDF documents", type=["pdf"], accept_multiple_files=True)
if uploads:
    try:
        with st.spinner("Reading PDFs and preparing searchable chunks..."):
            docs, vectorstore, document_names = process_pdfs(uploads)
        st.session_state["docs"] = docs
        st.session_state["vectorstore"] = vectorstore
        st.session_state["document_names"] = document_names
        st.success(f"Indexed {len(document_names)} PDF(s) into {len(docs)} searchable chunks.")
        with st.expander("Documents loaded"):
            for name in document_names:
                st.write(f"📄 {name}")
    except Exception as e:
        st.error(f"Could not process PDF(s): {e}")
        st.stop()

if "vectorstore" not in st.session_state:
    st.info("Upload one or more PDFs to begin. Scanned/image-only PDFs may require OCR before text can be extracted.")
    st.stop()

tabs = st.tabs(["💬 Ask PDF", "🧠 Adaptive Quiz", "🔬 Compare PDFs", "📊 Learning Analytics", "📝 Study Tools", "🕘 History"])

with tabs[0]:
    st.subheader("Ask questions with page-level evidence")
    question = st.text_input("Your question", placeholder="What are the key findings in these documents?")
    k = st.slider("Number of evidence passages", 2, 8, 4)
    if st.button("Get evidence-based answer", type="primary"):
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            with st.spinner("Retrieving evidence and verifying the draft answer..."):
                passages = retrieve_context(st.session_state["vectorstore"], question, k=k)
                result = answer_question(question, passages)
            st.markdown("### Answer")
            st.write(result["answer"])
            if result["supported"]:
                st.success("Evidence check: supporting passages were found. This is a heuristic check, not a guarantee of factual correctness.")
            else:
                st.warning("Evidence check: the answer may not be supported by the retrieved passages. Treat it as unverified.")
            st.markdown("### Sources")
            for i, p in enumerate(passages, 1):
                meta = p.metadata
                with st.expander(f"[{i}] {meta.get('source', 'PDF')} — page {meta.get('page', '?')}"):
                    st.write(p.page_content)
            save_chat(question, result["answer"], [f"{p.metadata.get('source')} p.{p.metadata.get('page')}" for p in passages])

with tabs[1]:
    st.subheader("Generate a quiz from your PDFs")
    c1, c2, c3 = st.columns(3)
    with c1:
        qtype = st.selectbox("Question type", ["MCQ", "True/False", "Short answer", "Mixed"])
    with c2:
        n_questions = st.slider("Number of questions", 3, 15, 5)
    with c3:
        prior = get_quiz_history(limit=20)
        latest_score = prior[0]["score_pct"] if prior else None
        if latest_score is None:
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=1)
        else:
            adaptive = "Easy" if latest_score < 50 else ("Medium" if latest_score < 80 else "Hard")
            difficulty = st.selectbox("Difficulty (suggested from last score)", ["Easy", "Medium", "Hard"], index=["Easy","Medium","Hard"].index(adaptive))
            st.caption(f"Suggested: {adaptive} based on your latest saved quiz score ({latest_score:.0f}%).")
    if st.button("Generate quiz"):
        with st.spinner("Creating questions from your documents..."):
            context = retrieve_context(st.session_state["vectorstore"], "important concepts definitions key facts and explanations", k=8)
            quiz = generate_quiz(context, n_questions, qtype, difficulty)
        if not quiz:
            st.error("The AI did not return a usable quiz. Try again or use fewer questions.")
        else:
            st.session_state["active_quiz"] = quiz
            st.session_state["quiz_answers"] = {}
            st.session_state["quiz_submitted"] = False
    quiz = st.session_state.get("active_quiz", [])
    if quiz:
        with st.form("quiz_form"):
            for i, item in enumerate(quiz):
                st.markdown(f"**Q{i+1}. {item.get('question','')}**")
                options = item.get("options") or []
                if item.get("type") == "Short answer":
                    val = st.text_input("Your answer", key=f"quiz_{i}")
                else:
                    choices = options if options else ["True", "False"]
                    val = st.radio("Choose one", choices, key=f"quiz_{i}")
                st.session_state["quiz_answers"][str(i)] = val
            submitted = st.form_submit_button("Submit answers")
        if submitted:
            correct = 0
            reviewed = []
            topic_results = {}
            for i, item in enumerate(quiz):
                user_ans = st.session_state["quiz_answers"].get(str(i), "")
                correct_ans = str(item.get("answer", "")).strip()
                if item.get("type") == "Short answer":
                    is_correct = evaluate_short_answer(user_ans, correct_ans, item.get("explanation", ""))
                else:
                    is_correct = user_ans.strip().lower() == correct_ans.lower()
                correct += int(is_correct)
                topic = item.get("topic", "General")
                topic_results.setdefault(topic, []).append(int(is_correct))
                reviewed.append((item, user_ans, is_correct))
            score_pct = 100 * correct / len(quiz)
            save_quiz_attempt(score_pct, len(quiz), difficulty, topic_results)
            st.session_state["quiz_submitted"] = True
            st.session_state["quiz_review"] = reviewed
            st.session_state["quiz_score"] = score_pct
            st.rerun()
    if st.session_state.get("quiz_submitted"):
        score = st.session_state.get("quiz_score", 0)
        st.metric("Quiz score", f"{score:.0f}%")
        for i, (item, user_ans, is_correct) in enumerate(st.session_state.get("quiz_review", []), 1):
            st.markdown(f"**Q{i}. {item.get('question','')}**")
            st.write(f"Your answer: {user_ans or 'No answer'}")
            st.write(f"Correct answer: {item.get('answer','')}")
            st.write(("✅ Correct" if is_correct else "❌ Incorrect") + f" — {item.get('explanation','')}")
        if score < 60:
            st.info("Recommendation: review the explanations and try an Easy quiz.")
        elif score < 80:
            st.info("Recommendation: revise missed topics and try Medium difficulty.")
        else:
            st.success("Good progress! Try a Hard quiz to deepen your understanding.")

with tabs[2]:
    st.subheader("Compare multiple PDFs")
    names = st.session_state["document_names"]
    if len(names) < 2:
        st.info("Upload at least two PDFs to compare them.")
    else:
        selected = st.multiselect("Select documents to compare", names, default=names[:min(3, len(names))])
        focus = st.text_input("Comparison focus", "methods, findings, similarities, differences, and limitations")
        if st.button("Compare selected documents"):
            with st.spinner("Comparing evidence from selected PDFs..."):
                result = compare_documents(st.session_state["docs"], selected, focus)
            st.markdown(result)

with tabs[3]:
    st.subheader("Knowledge-gap analysis")
    history = get_quiz_history(limit=100)
    if not history:
        st.info("Complete at least one quiz to see your progress and weak topics.")
    else:
        scores = [h["score_pct"] for h in history]
        a, b, c = st.columns(3)
        a.metric("Quizzes completed", len(history))
        b.metric("Latest score", f"{scores[0]:.0f}%")
        c.metric("Average score", f"{sum(scores)/len(scores):.0f}%")
        st.line_chart({"Score (%)": list(reversed(scores))})
        topics = topic_accuracy()
        if topics:
            st.markdown("#### Topic mastery")
            st.bar_chart({k: v for k, v in topics.items()})
            weak = recommend_revision(topics)
            st.markdown("#### Recommended revision")
            for topic in weak:
                st.write(f"🔁 **{topic}** — revisit the relevant PDF pages and take a targeted quiz.")
        st.caption("Scores are based on quizzes completed in this local app database.")

with tabs[4]:
    st.subheader("Study tools")
    tool = st.selectbox("Choose a tool", ["Summary", "Flashcards", "Study plan"])
    if tool == "Summary":
        style = st.selectbox("Summary style", ["Concise", "Detailed", "Exam revision"])
        if st.button("Generate summary"):
            ctx = retrieve_context(st.session_state["vectorstore"], "main ideas headings important facts conclusions", k=8)
            with st.spinner("Summarizing..."):
                st.markdown(summarize_documents(ctx, style))
    elif tool == "Flashcards":
        count = st.slider("Number of flashcards", 3, 20, 8)
        if st.button("Generate flashcards"):
            ctx = retrieve_context(st.session_state["vectorstore"], "definitions concepts key terms and explanations", k=8)
            cards = make_flashcards(ctx, count)
            for i, card in enumerate(cards, 1):
                with st.expander(f"Card {i}: {card.get('front','Term')}"):
                    st.write(card.get("back", ""))
    else:
        days = st.slider("Study plan length (days)", 1, 14, 5)
        hours = st.slider("Study hours per day", 1, 8, 2)
        if st.button("Create study plan"):
            ctx = retrieve_context(st.session_state["vectorstore"], "document topics chapters concepts and learning objectives", k=8)
            st.markdown(build_study_plan(ctx, days, hours))

with tabs[5]:
    st.subheader("Saved activity")
    st.markdown("#### Recent quiz attempts")
    hist = get_quiz_history(limit=20)
    if hist:
        st.dataframe(hist, use_container_width=True)
    else:
        st.write("No quiz attempts saved yet.")
    st.markdown("#### Recent chat questions")
    chats = get_chat_history(limit=20)
    if chats:
        for item in chats:
            with st.expander(item["question"][:100]):
                st.write(item["answer"])
                st.caption(item["created_at"])
    else:
        st.write("No chat history saved yet.")
