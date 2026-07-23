// Backend runs on the same host that served this page, on port 8001.
// Deriving it from window.location means the app works whether you open it at
// http://localhost:8000 (desktop) or http://<your-lan-ip>:8000 (phone/another device)
// without editing this file. To point at a fixed backend, replace this with a URL string.
const BACKEND_PORT = 8001;
export const RAG_BACKEND =
  window.location.protocol === "file:" || !window.location.hostname
    ? `http://localhost:${BACKEND_PORT}`
    : `${window.location.protocol}//${window.location.hostname}:${BACKEND_PORT}`;

export const STORAGE_KEYS = {
  chats: "local_llm_chats",
  activeChat: "local_llm_active_chat",
  theme: "local_llm_theme",
};

export const ATTACHMENT_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "gif", "webp"];
