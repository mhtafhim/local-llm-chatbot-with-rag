# Local LLM Chatbot with RAG

A ChatGPT-style web interface for your **local Ollama** models with document-based RAG (PDF, DOCX, TXT) support.
---

## 📸 Preview

### Desktop View
![Desktop Interface](assets/img/screenshot1.png)

### Mobile Responsive View
![Mobile Interface](assets/img/screenshot2.png)

---

---

## ✨ Features

- 💬 ChatGPT-style UI (sidebar, multiple chats, markdown, code blocks with copy)
- 📚 RAG — chat with your own PDF/DOCX/TXT documents
- 🌊 Streaming responses (live typing effect)
- 📱 Mobile responsive
- 💾 Chat history saved in browser
- 🗑️ One-click clear vector database
- 🐧 Fedora/Linux-friendly backend startup script

---

## 📁 Project Structure

```
local-llm-chatbot-with-rag/
├── frontend/
│   └── index.html        → Frontend (chat UI)
├── backend/
│   ├── main.py            → FastAPI entrypoint
│   ├── app/
│   │   ├── config.py      → Provider and RAG settings
│   │   ├── documents.py   → Upload, ingest, ChromaDB retrieval
│   │   ├── routes.py      → API routes
│   │   ├── web_search.py
│   │   └── llm/           → Ollama and LM Studio providers
│   ├── requirements.txt
│   ├── config.example     → Copy to .env for local provider settings
│   ├── start.sh           → Linux start script
│   ├── start.bat          → Old Windows launcher
│   └── docs/               → Your documents go here (auto-ignored by git)
├── .gitignore
├── LICENSE
└── README.md
```

---

## ⚙️ Requirements

- [Ollama](https://ollama.com/) running locally
- A chat model, for example `gemma4:e4b`
- An embedding model, for example `nomic-embed-text`
- Python 3.10+
- A modern browser

---

## 🚀 Setup

### 1. Start Ollama

```bash
ollama serve
```

In another terminal, pull the default models:

```bash
ollama pull gemma4:e4b
ollama pull nomic-embed-text
```

### 2. Run the backend

```bash
cd backend
chmod +x start.sh
./start.sh
```

The defaults are:

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE=http://localhost:11434
OLLAMA_CHAT_MODEL=gemma4:e4b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

To use different models:

```bash
OLLAMA_CHAT_MODEL=qwen2.5 OLLAMA_EMBED_MODEL=nomic-embed-text ./start.sh
```

For repeated use, copy `backend/config.example` to `backend/.env` and edit it:

```bash
cd backend
cp config.example .env
./start.sh
```

To switch back to LM Studio quickly:

```bash
LLM_PROVIDER=lmstudio \
LMSTUDIO_BASE=http://localhost:1234/v1 \
LMSTUDIO_CHAT_MODEL=your-chat-model \
LMSTUDIO_EMBED_MODEL=your-embedding-model \
./start.sh
```

You can also edit the defaults in `backend/app/config.py` if you prefer source-level configuration.

### 3. Serve the frontend

```bash
cd frontend
python -m http.server 8000
```

### 4. Open in browser

```text
http://localhost:8000
```

---

## 📤 Adding Documents

- Click **"+ Upload PDF / DOCX / TXT"** in the sidebar, **or**
- Drop files into `backend/docs/` and call `POST /rescan`

## 🗑️ Clearing Documents

Click **"🗑️ Clear All Documents"** in the sidebar — wipes the vector DB and docs folder.

---

## ⚠️ Notes

- Ollama must stay running for chat and document ingestion to work
- The frontend talks to the FastAPI backend at `http://localhost:8001`
- If you open the frontend from another device, update `RAG_BACKEND` in `frontend/index.html` to your Fedora machine's LAN IP

---

## 📄 License

MIT — free to use and modify.
