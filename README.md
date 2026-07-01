# Local LLM Chatbot with RAG 🖥️

A ChatGPT-style web interface for your **local LM Studio** models — with document-based RAG (PDF, DOCX, TXT) support.

---

## ✨ Features

- 💬 ChatGPT-style UI (sidebar, multiple chats, markdown, code blocks with copy)
- 📚 RAG — chat with your own PDF/DOCX/TXT documents
- 🌊 Streaming responses (live typing effect)
- 📱 Mobile responsive
- 💾 Chat history saved in browser
- 🗑️ One-click clear vector database
- 🔁 Auto-fallback to direct LM Studio chat if RAG backend is offline

---

## 📁 Project Structure

```
local-llm-chatbot-with-rag/
├── frontend/
│   └── index.html        → Frontend (chat UI)
├── backend/
│   ├── main.py            → FastAPI RAG backend
│   ├── requirements.txt
│   ├── start.bat          → One-click start (Windows)
│   └── docs/               → Your documents go here (auto-ignored by git)
├── .gitignore
├── LICENSE
└── README.md
```

---

## ⚙️ Requirements

- [LM Studio](https://lmstudio.ai/) running locally with:
  - A chat model loaded
  - An embedding model loaded (e.g. `nomic-embed-text`)
  - Server mode enabled + **CORS enabled**
- Python 3.10+
- A modern browser

---

## 🚀 Setup

### 1. Start LM Studio
- Load a chat model + an embedding model
- Go to **Settings → Server** → enable **CORS**
- Note your LM Studio server address (e.g. `http://192.168.x.x:1234`)

### 2. Configure the backend
Open `backend/main.py` and update:
```python
LM_STUDIO_BASE = "http://YOUR_LM_STUDIO_IP:1234/v1"
EMBED_MODEL = "your-embedding-model-name"
```

### 3. Configure the frontend
Open `index.html` and update:
```js
const LM_STUDIO_BASE = "http://YOUR_LM_STUDIO_IP:1234/v1";
const RAG_BACKEND = "http://YOUR_BACKEND_IP:8001";
```

### 4. Run the backend
```
cd backend
start.bat
```
(or manually: `pip install -r requirements.txt` → `uvicorn main:app --host 0.0.0.0 --port 8001`)

### 5. Serve the frontend
```
cd frontend
python -m http.server 8000
```

### 6. Open in browser
```
http://YOUR_IP:8000
```

---

## 📤 Adding Documents

- Click **"+ Upload PDF / DOCX / TXT"** in the sidebar, **or**
- Drop files into `backend/docs/` and call `POST /rescan`

## 🗑️ Clearing Documents

Click **"🗑️ Clear All Documents"** in the sidebar — wipes the vector DB and docs folder.

---

## ⚠️ Notes

- This project uses **local IPs** — only works within your local network
- LM Studio server must stay running for chat to work
- If RAG backend is offline, chat still works directly via LM Studio (no document context)

---

## 📄 License

MIT — free to use and modify.
