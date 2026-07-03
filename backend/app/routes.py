from fastapi import APIRouter, File, UploadFile
from fastapi.responses import StreamingResponse

from app.config import Settings
from app.documents import DocumentService
from app.llm.base import LLMProvider
from app.schemas import ChatRequest
from app.web_search import web_search


def create_router(
    settings: Settings, provider: LLMProvider, documents: DocumentService
) -> APIRouter:
    router = APIRouter()

    @router.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        count = documents.upload_file(file)
        return {"filename": file.filename, "chunks_added": count}

    @router.get("/documents")
    def list_documents():
        return {"documents": documents.list_documents()}

    @router.post("/rescan")
    def rescan():
        return documents.scan_docs_folder()

    @router.post("/chat")
    async def chat(payload: ChatRequest):
        messages = payload.messages
        user_query = messages[-1]["content"] if messages else ""
        context_block = ""
        sources = []

        if payload.use_rag:
            context_block, sources = documents.retrieve_context(user_query)

        if payload.use_web_search:
            web_results = web_search(user_query)
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

        system_prompt = build_system_prompt(context_block)
        final_messages = [{"role": "system", "content": system_prompt}] + messages
        headers = {"X-Sources": safe_header(",".join(sources))} if sources else {}
        return StreamingResponse(
            provider.chat_stream(final_messages),
            media_type="text/event-stream",
            headers=headers,
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
