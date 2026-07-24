import base64
import mimetypes
import os
import shutil
import tempfile

import chromadb
from fastapi import UploadFile
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Settings
from app.embeddings import ProviderEmbeddingFunction
from app.llm.base import LLMProvider

TEMP_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


class DocumentService:
    def __init__(self, settings: Settings, provider: LLMProvider):
        self.settings = settings
        self.embed_fn = ProviderEmbeddingFunction(provider)
        os.makedirs(settings.docs_folder, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=settings.chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="documents", embedding_function=self.embed_fn
        )

    def load_file(self, path: str):
        ext = path.lower().split(".")[-1]
        if ext == "pdf":
            return PyPDFLoader(path).load()
        if ext == "docx":
            return Docx2txtLoader(path).load()
        if ext in ("txt", "md"):
            return TextLoader(path, encoding="utf-8").load()
        return []

    def ingest_file(self, path: str, filename: str, force: bool = False) -> int:
        if not force:
            try:
                existing = self.collection.get(where={"source": filename})
                if existing["ids"]:
                    return len(existing["ids"])
            except Exception:
                pass

        docs = self.load_file(path)
        if not docs:
            return 0

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )
        chunks = splitter.split_documents(docs)

        ids, texts, metadatas = [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{filename}__{i}")
            texts.append(chunk.page_content)
            metadatas.append({"source": filename, "chunk": i})

        if texts:
            try:
                existing = self.collection.get(where={"source": filename})
                if existing["ids"]:
                    self.collection.delete(ids=existing["ids"])
            except Exception:
                pass
            self.collection.add(ids=ids, documents=texts, metadatas=metadatas)
        return len(texts)

    def scan_docs_folder(self, force: bool = False) -> dict[str, int | str]:
        results = {}
        for fname in os.listdir(self.settings.docs_folder):
            fpath = os.path.join(self.settings.docs_folder, fname)
            if os.path.isfile(fpath):
                try:
                    results[fname] = self.ingest_file(fpath, fname, force=force)
                except Exception as exc:
                    results[fname] = f"ERROR: {exc}"
        return results

    def list_documents(self) -> list[str]:
        return os.listdir(self.settings.docs_folder)

    def upload_file(self, file: UploadFile) -> int:
        dest = os.path.join(self.settings.docs_folder, file.filename)
        with open(dest, "wb") as target:
            shutil.copyfileobj(file.file, target)
        return self.ingest_file(dest, file.filename)

    def extract_temporary(self, file: UploadFile) -> dict:
        """Read a PDF/image for one-off analysis without touching docs_folder or the vector DB."""
        filename = file.filename or "upload"
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        raw = file.file.read()

        if ext == "pdf":
            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            try:
                tmp.write(raw)
                tmp.close()
                docs = PyPDFLoader(tmp.name).load()
            except Exception as exc:
                raise ValueError(f"Could not read PDF: {exc}") from exc
            finally:
                os.unlink(tmp.name)
            text = "\n\n".join(doc.page_content for doc in docs)
            return {"type": "pdf", "filename": filename, "content": text}

        if ext in TEMP_IMAGE_EXTENSIONS:
            mime = mimetypes.guess_type(filename)[0] or (
                "image/jpeg" if ext == "jpg" else f"image/{ext}"
            )
            return {
                "type": "image",
                "filename": filename,
                "content": base64.b64encode(raw).decode("ascii"),
                "mime_type": mime,
            }

        raise ValueError(f"Unsupported attachment type: .{ext}" if ext else "Unsupported attachment type")

    def retrieve_context(self, query: str) -> tuple[str, list[str]]:
        if self.collection.count() <= 0:
            return "", []
        results = self.collection.query(query_texts=[query], n_results=self.settings.top_k)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        if not docs:
            return "", []
        context = "\n\n".join(
            f"[Source: {meta['source']}]\n{doc}" for doc, meta in zip(docs, metas)
        )
        sources = list({meta["source"] for meta in metas})
        return context, sources

    def clear(self) -> None:
        try:
            self.chroma_client.delete_collection("documents")
        except Exception:
            pass
        self.collection = self.chroma_client.get_or_create_collection(
            name="documents", embedding_function=self.embed_fn
        )
        for fname in os.listdir(self.settings.docs_folder):
            fpath = os.path.join(self.settings.docs_folder, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)
