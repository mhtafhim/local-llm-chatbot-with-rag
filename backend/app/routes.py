import json
from collections.abc import Iterable

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.config import Settings
from app.documents import DocumentService
from app.llm.base import LLMProvider
from app.schemas import Attachment, ChatRequest
from app.web_search import web_search


def create_router(
    settings: Settings, provider: LLMProvider, documents: DocumentService
) -> APIRouter:
    router = APIRouter()

    @router.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        count = documents.upload_file(file)
        return {"filename": file.filename, "chunks_added": count}

    @router.post("/analyze-upload")
    async def analyze_upload(file: UploadFile = File(...)):
        try:
            return documents.extract_temporary(file)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/documents")
    def list_documents():
        return {"documents": documents.list_documents()}

    @router.post("/rescan")
    def rescan():
        return documents.scan_docs_folder()

    @router.post("/chat")
    async def chat(payload: ChatRequest):
        return StreamingResponse(
            chat_event_stream(payload, provider, documents),
            media_type="text/event-stream",
        )

    @router.post("/clear")
    def clear_db():
        documents.clear()
        return {"status": "cleared"}

    @router.get("/")
    def root():
        return {
            "status": "RAG backend running",
            **provider.status(),
            "documents": len(documents.list_documents()),
            "docs_folder": settings.docs_folder,
            "chroma_path": settings.chroma_path,
        }

    return router


def chat_event_stream(
    payload: ChatRequest, provider: LLMProvider, documents: DocumentService
) -> Iterable[bytes]:
    messages = [dict(message) for message in payload.messages]
    user_query = messages[-1]["content"] if messages else ""
    context_block = ""
    sources = []

    attachments = payload.attachments or []
    pdf_attachments = [a for a in attachments if a.type == "pdf"]
    image_attachments = [a for a in attachments if a.type == "image"]

    if pdf_attachments:
        yield sse({"type": "status", "status": "Reading attached file(s)..."})
        context_block = "\n\n".join(
            f"[Temporary attachment: {a.filename}]\n{a.content}" for a in pdf_attachments
        )

    if payload.use_rag:
        rag_context, rag_sources = documents.retrieve_context(user_query)
        if rag_context:
            context_block = f"{context_block}\n\n{rag_context}" if context_block else rag_context
        if rag_sources:
            sources += rag_sources
            yield sse({"type": "sources", "sources": sources})

    if payload.use_web_search:
        yield sse({"type": "status", "status": "Searching web..."})
        web_results = web_search(user_query)
        yield sse({"type": "web_results", "results": web_results})
        if web_results:
            web_block = "\n\n".join(
                f"[Web: {r['title']} ({r['url']})]\n{r['snippet']}"
                for r in web_results
            )
            context_block = (
                f"{context_block}\n\n{web_block}" if context_block else web_block
            )
            sources += [
                r["title"] for r in web_results if r["title"] != "Search failed"
            ]
            yield sse({"type": "sources", "sources": sources})
        yield sse({"type": "status", "status": "Thinking..."})

    system_prompt = build_system_prompt(context_block)
    final_messages = [{"role": "system", "content": system_prompt}] + messages

    if image_attachments:
        attach_images(final_messages[-1], image_attachments, provider.name)

    yield from provider.chat_stream(final_messages, thinking=payload.use_thinking)


def attach_images(message: dict, images: list[Attachment], provider_name: str) -> None:
    if provider_name == "ollama":
        message["images"] = [image.content for image in images]
        return

    text = message.get("content", "")
    message["content"] = [{"type": "text", "text": text}] + [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{image.mime_type or 'image/png'};base64,{image.content}"},
        }
        for image in images
    ]


def sse(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")


def build_system_prompt(context_block: str) -> str:
    if not context_block:
        return "You are a helpful assistant."
    return (
        "You are a helpful assistant. Use the following context (documents and/or web "
        "search results) to answer the user's question if relevant. Mention if info "
        "came from web search. If context doesn't contain the answer, say so and answer "
        "from general knowledge.\n\nCONTEXT:\n"
        + context_block
    )


def safe_header(text: str) -> str:
    return text.encode("ascii", errors="ignore").decode("ascii")
