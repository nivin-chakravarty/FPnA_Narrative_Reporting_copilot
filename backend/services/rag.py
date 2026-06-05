from __future__ import annotations
from pathlib import Path
from dotenv import load_dotenv
import os
load_dotenv()
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FAISS_DIR = Path(__file__).resolve().parents[2] / "faiss_index"

def read_context() -> tuple[str, str]:
    glossary = (DATA_DIR / "finance_glossary.md").read_text(encoding="utf-8") if (DATA_DIR / "finance_glossary.md").exists() else ""
    policy = (DATA_DIR / "accounting_policy_notes.md").read_text(encoding="utf-8") if (DATA_DIR / "accounting_policy_notes.md").exists() else ""
    return glossary, policy

def build_or_load_vectorstore():
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_core.documents import Document
    emb = HuggingFaceEmbeddings(model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    if FAISS_DIR.exists():
        return FAISS.load_local(str(FAISS_DIR), emb, allow_dangerous_deserialization=True)
    glossary, policy = read_context()
    docs = [Document(page_content=glossary, metadata={"source":"finance_glossary"}), Document(page_content=policy, metadata={"source":"accounting_policy_notes"})]
    db = FAISS.from_documents(docs, emb)
    db.save_local(str(FAISS_DIR))
    return db

def retrieve_context(query: str, k: int = 2) -> str:
    try:
        db = build_or_load_vectorstore()
        docs = db.similarity_search(query, k=k)
        return "\n\n".join([d.page_content for d in docs])
    except Exception:
        glossary, policy = read_context()
        return glossary + "\n\n" + policy
