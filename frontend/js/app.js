import { analyzeUpload, clearDocuments, getBackendStatus, listDocuments, streamChat, uploadDocument } from "./api.js?v=3";
import { ATTACHMENT_EXTENSIONS, STORAGE_KEYS } from "./config.js?v=3";
import { ChatRenderer } from "./render.js?v=3";
import { ChatStore } from "./store.js?v=3";
import { isMobileViewport } from "./utils.js?v=3";

const elements = {
  overlay: document.getElementById("overlay"),
  sidebar: document.getElementById("sidebar"),
  newChatBtn: document.getElementById("newChatBtn"),
  chatList: document.getElementById("chatList"),
  docList: document.getElementById("docList"),
  uploadBtn: document.getElementById("uploadBtn"),
  fileInput: document.getElementById("fileInput"),
  clearDbBtn: document.getElementById("clearDbBtn"),
  menuBtn: document.getElementById("menuBtn"),
  chat: document.getElementById("chat"),
  modelStatus: document.getElementById("modelStatus"),
  themeToggleBtn: document.getElementById("themeToggleBtn"),
  ragPill: document.getElementById("ragPill"),
  webPill: document.getElementById("webPill"),
  thinkingPill: document.getElementById("thinkingPill"),
  attachPill: document.getElementById("attachPill"),
  attachInput: document.getElementById("attachInput"),
  attachmentPreview: document.getElementById("attachmentPreview"),
  userInput: document.getElementById("userInput"),
  stopBtn: document.getElementById("stopBtn"),
  sendBtn: document.getElementById("sendBtn"),
};

const store = new ChatStore();
const renderer = new ChatRenderer(elements);

const tools = {
  useRag: true,
  useWebSearch: false,
  useThinking: true,
};

let activeChatAbortController = null;
let pendingAttachments = [];

init();

function init() {
  bindEvents();
  initTheme();
  renderCurrentState();
  autoGrow(elements.userInput);
  detectModel();
  loadDocs();
}

function bindEvents() {
  elements.newChatBtn.addEventListener("click", createNewChat);
  elements.chatList.addEventListener("click", handleChatListClick);
  elements.overlay.addEventListener("click", () => renderer.toggleSidebar());
  elements.menuBtn.addEventListener("click", () => renderer.toggleSidebar());
  elements.uploadBtn.addEventListener("click", () => elements.fileInput.click());
  elements.fileInput.addEventListener("change", () => uploadFiles(elements.fileInput.files));
  elements.clearDbBtn.addEventListener("click", clearDb);
  elements.ragPill.addEventListener("click", () => toggleTool("rag"));
  elements.webPill.addEventListener("click", () => toggleTool("web"));
  elements.thinkingPill.addEventListener("click", () => toggleTool("thinking"));
  elements.attachPill.addEventListener("click", () => elements.attachInput.click());
  elements.attachInput.addEventListener("change", () => handleAttachFiles(elements.attachInput.files));
  elements.attachmentPreview.addEventListener("click", handleAttachmentPreviewClick);
  elements.themeToggleBtn.addEventListener("click", toggleTheme);
  elements.sendBtn.addEventListener("click", sendMessage);
  elements.stopBtn.addEventListener("click", stopActiveResponse);
  elements.userInput.addEventListener("input", () => autoGrow(elements.userInput));
  elements.userInput.addEventListener("keydown", handleComposerKeydown);
}

function initTheme() {
  let saved = "dark";
  try {
    saved = localStorage.getItem(STORAGE_KEYS.theme) === "light" ? "light" : "dark";
  } catch {
    // localStorage may be unavailable (private mode); fall back to dark
  }
  applyTheme(saved);
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(STORAGE_KEYS.theme, theme);
  } catch {
    // ignore persistence failure; theme still applies for this session
  }
  elements.themeToggleBtn.textContent = theme === "light" ? "🌙" : "☀️";
}

function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light");
}

function renderCurrentState() {
  renderer.renderSidebar(store.listChatEntries(), store.activeChatId);
  renderer.renderMessages(store.activeChat.messages);
}

function createNewChat() {
  store.createChat();
  renderCurrentState();
}

function handleChatListClick(event) {
  const deleteChatId = event.target.dataset.deleteChatId;
  if (deleteChatId) {
    event.stopPropagation();
    deleteChat(deleteChatId);
    return;
  }

  const chatItem = event.target.closest("[data-chat-id]");
  if (!chatItem) return;

  store.setActiveChat(chatItem.dataset.chatId);
  renderCurrentState();
  if (isMobileViewport()) renderer.setSidebarOpen(false);
}

function deleteChat(id) {
  if (!confirm("Delete this chat?")) return;
  store.deleteChat(id);
  renderCurrentState();
}

function toggleTool(type) {
  if (type === "rag") {
    tools.useRag = !tools.useRag;
    elements.ragPill.classList.toggle("active", tools.useRag);
    return;
  }

  if (type === "thinking") {
    tools.useThinking = !tools.useThinking;
    elements.thinkingPill.classList.toggle("active", tools.useThinking);
    return;
  }

  tools.useWebSearch = !tools.useWebSearch;
  elements.webPill.classList.toggle("active", tools.useWebSearch);
}

function handleComposerKeydown(event) {
  if (event.key !== "Enter" || event.shiftKey) return;
  event.preventDefault();
  sendMessage();
}

function autoGrow(element) {
  element.style.height = "24px";
  const next = Math.min(element.scrollHeight, 180);
  element.style.height = `${next}px`;
  element.style.overflowY = element.scrollHeight > 180 ? "auto" : "hidden";
}

const PROVIDER_LABELS = { ollama: "Ollama", lmstudio: "LM Studio" };

async function detectModel() {
  try {
    const data = await getBackendStatus();
    const label = PROVIDER_LABELS[data?.provider] || data?.provider || "Backend";
    renderer.setModelStatus(data?.chat_model ? `${label}: ${data.chat_model}` : `${label} connected`);
  } catch {
    renderer.setModelStatus("RAG backend not reachable");
  }
}

async function loadDocs() {
  try {
    const data = await listDocuments();
    renderer.renderDocuments(data.documents || []);
  } catch {
    renderer.renderDocumentsError();
  }
}

async function clearDb() {
  if (!confirm("Delete ALL uploaded documents from the vector DB? This cannot be undone.")) return;

  try {
    await clearDocuments();
    await loadDocs();
    alert("All documents cleared");
  } catch (error) {
    alert(`Failed to clear: ${error.message}`);
  }
}

async function uploadFiles(files) {
  for (const file of files) {
    try {
      await uploadDocument(file);
    } catch (error) {
      alert(`Upload failed: ${error.message}`);
    }
  }

  elements.fileInput.value = "";
  loadDocs();
}

async function handleAttachFiles(files) {
  for (const file of Array.from(files)) {
    const ext = file.name.toLowerCase().split(".").pop();
    if (!ATTACHMENT_EXTENSIONS.includes(ext)) {
      alert(`Unsupported attachment type: .${ext}`);
      continue;
    }

    const pending = { filename: file.name, type: ext === "pdf" ? "pdf" : "image", loading: true };
    pendingAttachments.push(pending);
    renderPendingAttachments();

    try {
      const result = await analyzeUpload(file);
      Object.assign(pending, result, { loading: false });
    } catch (error) {
      pendingAttachments = pendingAttachments.filter((attachment) => attachment !== pending);
      alert(`Failed to read ${file.name}: ${error.message}`);
    }

    renderPendingAttachments();
  }

  elements.attachInput.value = "";
}

function handleAttachmentPreviewClick(event) {
  const index = event.target.dataset.removeAttachment;
  if (index === undefined) return;
  pendingAttachments.splice(Number(index), 1);
  renderPendingAttachments();
}

function renderPendingAttachments() {
  elements.attachmentPreview.hidden = pendingAttachments.length === 0;
  elements.attachmentPreview.innerHTML = pendingAttachments
    .map((attachment, index) => {
      const icon = attachment.type === "image" ? "🖼" : "📄";
      const label = attachment.loading ? `Reading ${attachment.filename}...` : attachment.filename;
      return `<span class="attachmentChip${attachment.loading ? " loading" : ""}">${icon} ${label}<span class="attachmentRemove" data-remove-attachment="${index}">×</span></span>`;
    })
    .join("");
}

async function sendMessage() {
  if (activeChatAbortController) return;

  const rawText = elements.userInput.value.trim();
  const readyAttachments = pendingAttachments.filter((attachment) => !attachment.loading);
  if (!rawText && !readyAttachments.length) return;

  const text = rawText || "Please analyze the attached file(s).";
  const attachmentsMeta = readyAttachments.map(({ filename, type }) => ({ filename, type }));

  elements.userInput.value = "";
  autoGrow(elements.userInput);
  pendingAttachments = [];
  renderPendingAttachments();
  renderer.setSending(true);
  activeChatAbortController = new AbortController();

  store.addMessage({ role: "user", content: text, attachments: attachmentsMeta });
  store.updateTitleFromPrompt(text);
  renderer.addBubble({ role: "user", text, attachments: attachmentsMeta });
  renderer.renderSidebar(store.listChatEntries(), store.activeChatId);

  const assistantState = {
    text: "",
    thinking: "",
    sources: [],
    webResults: [],
    webStatus: tools.useWebSearch ? "Waiting to search..." : "",
  };
  const assistantBubble = renderer.addBubble({ role: "assistant", text: "" });
  let shouldSaveAssistant = false;

  try {
    await streamChat({
      messages: store.activeChat.messages.map(({ role, content }) => ({ role, content })),
      useRag: tools.useRag,
      useWebSearch: tools.useWebSearch,
      useThinking: tools.useThinking,
      attachments: readyAttachments,
      signal: activeChatAbortController.signal,
      onEvent: (event) => handleChatStreamEvent(event, assistantState, assistantBubble),
    });

    renderer.refreshAssistantBubble(assistantBubble, assistantState);
    shouldSaveAssistant = true;
  } catch (error) {
    if (error.name === "AbortError") {
      renderer.refreshAssistantBubble(assistantBubble, assistantState);
      shouldSaveAssistant = true;
      return;
    }

    assistantBubble.innerHTML = `Error: ${error.message}<br><small>Is the RAG backend (backend/start.sh) running? Is Ollama running?</small>`;
    return;
  } finally {
    if (shouldSaveAssistant) saveAssistantMessage(assistantState);
    activeChatAbortController = null;
    renderer.setSending(false);
    elements.userInput.focus();
  }
}

function stopActiveResponse() {
  activeChatAbortController?.abort();
}

function saveAssistantMessage(assistantState) {
  if (
    !assistantState.text &&
    !assistantState.thinking &&
    !assistantState.sources.length &&
    !assistantState.webResults.length
  ) {
    return;
  }

  store.addMessage({
    role: "assistant",
    content: assistantState.text,
    thinking: assistantState.thinking,
    sources: assistantState.sources,
    webResults: assistantState.webResults,
  });
}

function handleChatStreamEvent(event, assistantState, assistantBubble) {
  if (event.type === "done") return;

  if (event.type === "status") {
    assistantState.webStatus = event.status || "";
    renderer.refreshAssistantBubble(assistantBubble, assistantState);
    return;
  }

  if (event.type === "web_results") {
    assistantState.webResults = event.results || [];
    assistantState.webStatus = assistantState.webResults.length ? "Web search results" : "No web results found";
    renderer.refreshAssistantBubble(assistantBubble, assistantState);
    return;
  }

  if (event.type === "sources") {
    assistantState.sources = event.sources || [];
    renderer.refreshAssistantBubble(assistantBubble, assistantState);
    return;
  }

  const delta = event?.choices?.[0]?.delta?.content;
  const reasoningDelta =
    event?.choices?.[0]?.delta?.reasoning_content ||
    event?.choices?.[0]?.delta?.reasoning ||
    event?.choices?.[0]?.delta?.thinking;

  if (reasoningDelta) {
    assistantState.thinking += reasoningDelta;
    renderer.refreshAssistantBubble(assistantBubble, assistantState);
  }

  if (delta) {
    assistantState.text += delta;
    renderer.refreshAssistantBubble(assistantBubble, assistantState);
  }
}
