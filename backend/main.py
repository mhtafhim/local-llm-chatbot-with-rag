"""
Local RAG Backend for LM Studio
--------------------------------
- Ingests PDFs, DOCX, TXT from ./docs folder
- Stores embeddings in ChromaDB (local, persistent)
- /chat endpoint: retrieves relevant chunks + calls LM Studio for final answer
- /upload endpoint: upload files from browser
- Auto re-scans docs folder on startup
"""

import os
import requests
import shutil
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import chromadb
from chromadb.utils import embedding_functions

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------- CONFIG ----------
LM_STUDIO_BASE = "http://192.168.10.40:1234/v1"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"  # change if your embed model id differs
CHAT_MODEL = None  # auto-detected from LM Studio if None
DOCS_FOLDER = "./docs"
CHROMA_PATH = "./chroma_db"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 4
# -----------------------------

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Sources"],
)

os.makedirs(DOCS_FOLDER, exist_ok=True)


# ---------- Embedding function using LM Studio ----------
class LMStudioEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __call__(self, input):
        embeddings = []
        for text in input:
            resp = requests.post(
                f"{LM_STUDIO_BASE}/embeddings",
                json={"model": EMBED_MODEL, "input": text},
                timeout=60,
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["data"][0]["embedding"])
        return embeddings


embed_fn = LMStudioEmbeddingFunction()

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection(
    name="documents", embedding_function=embed_fn
)


# ---------- Document loading ----------
def load_file(path):
    ext = path.lower().split(".")[-1]
    if ext == "pdf":
        return PyPDFLoader(path).load()
    elif ext == "docx":
        return Docx2txtLoader(path).load()
    elif ext in ("txt", "md"):
        return TextLoader(path, encoding="utf-8").load()
    else:
        return []


def ingest_file(path, filename, force=False):
    if not force:
        try:
            existing = collection.get(where={"source": filename})
            if existing["ids"]:
                return len(existing["ids"])  # already ingested, skip
        except Exception:
            pass

    docs = load_file(path)
    if not docs:
        return 0

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)

    ids, texts, metadatas = [], [], []
    for i, chunk in enumerate(chunks):
        ids.append(f"{filename}__{i}")
        texts.append(chunk.page_content)
        metadatas.append({"source": filename, "chunk": i})

    if texts:
        # remove old chunks from this file first (re-ingest safe)
        try:
            existing = collection.get(where={"source": filename})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass
        collection.add(ids=ids, documents=texts, metadatas=metadatas)
    return len(texts)


def scan_docs_folder(force=False):
    results = {}
    for fname in os.listdir(DOCS_FOLDER):
        fpath = os.path.join(DOCS_FOLDER, fname)
        if os.path.isfile(fpath):
            try:
                count = ingest_file(fpath, fname, force=force)
                results[fname] = count
            except Exception as e:
                results[fname] = f"ERROR: {e}"
    return results


import threading

@app.on_event("startup")
def startup_scan():
    def run():
        print("Scanning docs folder in background...")
        res = scan_docs_folder()
        print("Ingested:", res)
    threading.Thread(target=run, daemon=True).start()


# ---------- API: upload ----------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    dest = os.path.join(DOCS_FOLDER, file.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    count = ingest_file(dest, file.filename)
    return {"filename": file.filename, "chunks_added": count}


# ---------- API: list docs ----------
@app.get("/documents")
def list_documents():
    files = os.listdir(DOCS_FOLDER)
    return {"documents": files}


# ---------- API: rescan ----------
@app.post("/rescan")
def rescan():
    return scan_docs_folder()


def web_search(query, max_results=4):
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result")[:max_results]:
            title_el = r.select_one(".result__title")
            snippet_el = r.select_one(".result__snippet")
            link_el = r.select_one(".result__url")
            if title_el and snippet_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "snippet": snippet_el.get_text(strip=True),
                    "url": link_el.get_text(strip=True) if link_el else ""
                })
        return results
    except Exception as e:
        return [{"title": "Search failed", "snippet": str(e), "url": ""}]


# ---------- API: chat with RAG ----------
def get_model_name():
    global CHAT_MODEL
    if CHAT_MODEL:
        return CHAT_MODEL
    try:
        resp = requests.get(f"{LM_STUDIO_BASE}/models", timeout=10)
        models = resp.json().get("data", [])
        # skip embedding models
        for m in models:
            if "embed" not in m["id"].lower():
                return m["id"]
    except Exception:
        pass
    return "local-model"


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    use_rag: Optional[bool] = True
    use_web_search: Optional[bool] = False


@app.post("/chat")
async def chat(payload: ChatRequest):
    messages = payload.messages
    user_query = messages[-1]["content"] if messages else ""
    use_rag = payload.use_rag
    use_web_search = payload.use_web_search

    context_block = ""
    sources = []

    if use_rag and collection.count() > 0:
        results = collection.query(query_texts=[user_query], n_results=TOP_K)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        if docs:
            context_block += "\n\n".join(
                [f"[Source: {m['source']}]\n{d}" for d, m in zip(docs, metas)]
            )
            sources += list({m["source"] for m in metas})

    if use_web_search:
        web_results = web_search(user_query)
        if web_results:
            web_block = "\n\n".join(
                [f"[Web: {r['title']} ({r['url']})]\n{r['snippet']}" for r in web_results]
            )
            context_block = (context_block + "\n\n" + web_block) if context_block else web_block
            sources += [r["title"] for r in web_results if r["title"] != "Search failed"]

    system_prompt = (
        "You are a helpful assistant. Use the following context (documents and/or web "
        "search results) to answer the user's question if relevant. Mention if info "
        "came from web search. If context doesn't contain the answer, say so and answer "
        "from general knowledge.\n\nCONTEXT:\n" + context_block
        if context_block
        else "You are a helpful assistant."
    )

    final_messages = [{"role": "system", "content": system_prompt}] + messages

    def stream():
        with requests.post(
            f"{LM_STUDIO_BASE}/chat/completions",
            json={
                "model": get_model_name(),
                "messages": final_messages,
                "stream": True,
            },
            stream=True,
            timeout=300,
        ) as r:
            for line in r.iter_lines():
                if line:
                    yield line + b"\n"

    def safe_header(text):
        return text.encode("ascii", errors="ignore").decode("ascii")

    headers = {"X-Sources": safe_header(",".join(sources))} if sources else {}
    return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)


# ---------- API: clear vector DB ----------
@app.post("/clear")
def clear_db():
    global collection
    chroma_client.delete_collection("documents")
    collection = chroma_client.get_or_create_collection(
        name="documents", embedding_function=embed_fn
    )
    # also clear docs folder
    for fname in os.listdir(DOCS_FOLDER):
        fpath = os.path.join(DOCS_FOLDER, fname)
        if os.path.isfile(fpath):
            os.remove(fpath)
    return {"status": "cleared"}


@app.get("/")
def root():
    return {"status": "RAG backend running", "documents": len(os.listdir(DOCS_FOLDER))}