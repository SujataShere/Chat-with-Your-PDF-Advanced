from io import BytesIO
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pypdf import PdfReader

_EMBEDDINGS = None

def get_embeddings():
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _EMBEDDINGS

def process_pdfs(uploaded_files):
    raw_docs = []
    names = []
    for uploaded in uploaded_files:
        name = PathName = uploaded.name
        names.append(name)
        reader = PdfReader(BytesIO(uploaded.getvalue()))
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                raw_docs.append(Document(page_content=text, metadata={"source": name, "page": page_num}))
    if not raw_docs:
        raise ValueError("No extractable text was found. This may be a scanned PDF; run OCR first.")
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150, add_start_index=True)
    chunks = splitter.split_documents(raw_docs)
    vectorstore = FAISS.from_documents(chunks, get_embeddings())
    return chunks, vectorstore, names

def retrieve_context(vectorstore, query, k=4):
    return vectorstore.similarity_search(query, k=k)

def compare_documents(docs, selected_names, focus):
    selected = [d for d in docs if d.metadata.get("source") in selected_names]
    if not selected:
        return "No text found for the selected documents."
    # Keep evidence compact and label every passage with its source/page.
    passages = []
    for d in selected[:24]:
        passages.append(f"[{d.metadata.get('source')} | page {d.metadata.get('page')}]\n{d.page_content[:1200]}")
    from .ai_engine import call_llm
    prompt = f"""Compare the following PDF evidence. Focus: {focus}
Rules:
- Only make claims supported by supplied passages.
- Separate similarities, differences, methods, findings, and limitations where possible.
- Cite every finding as [document name, page N].
- If evidence is missing, say "Not stated in the provided excerpts".
- Do not invent document contents.

EVIDENCE:
{chr(10).join(passages)}
"""
    return call_llm(prompt, temperature=0.1, max_tokens=1800)

from pathlib import Path
