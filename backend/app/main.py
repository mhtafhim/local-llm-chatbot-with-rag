import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.documents import DocumentService
from app.llm import create_provider
from app.routes import create_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Sources"],
    )

    provider = create_provider(settings)
    documents = DocumentService(settings, provider)
    app.include_router(create_router(settings, provider, documents))

    @app.on_event("startup")
    def startup_scan():
        def run():
            print("Scanning docs folder in background...")
            result = documents.scan_docs_folder()
            print("Ingested:", result)

        threading.Thread(target=run, daemon=True).start()

    return app


app = create_app()
