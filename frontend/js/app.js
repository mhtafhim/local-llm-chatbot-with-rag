import { clearDocuments, getBackendStatus, listDocuments, streamChat, uploadDocument } from "./api.js";
import { ChatRenderer } from "./render.js";
import { ChatStore } from "./store.js";
import { isMobileViewport } from "./utils.js";

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
  ragPill: document.getElementById("ragPill"),
  webPill: document.getElementById("webPill"),
  userInput: document.getElementById("userInput"),
  stopBtn: document.getElementById("stopBtn"),
  sendBtn: document.getElementById("sendBtn"),
};

const store = new ChatStore();
const renderer = new ChatRenderer(elements);

const tools = {
  useRag: true,
  useWebSearch: false,
};

let activeChatAbortController = null;

init();

function init() {
  bindEvents();
  renderCurrentState();
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
  elements.sendBtn.addEventListener("click", sendMessage);
  elements.stopBtn.addEventListener("click", stopActiveResponse);
  elements.userInput.addEventListener("input", () => autoGrow(elements.userInput));
  elements.userInput.addEventListener("keydown", handleComposerKeydown);
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
  element.style.height = `${Math.min(element.scrollHeight, 160)}px`;
}

async function detectModel() {
  try {
    const data = await getBackendStatus();
    renderer.setModelStatus(data?.chat_model ? `Ollama: ${data.chat_model}` : "Ollama connected");
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

async function sendMessage() {
  if (activeChatAbortController) return;

  const text = elements.userInput.value.trim();
  if (!text) return;

  elements.userInput.value = "";
  autoGrow(elements.userInput);
  renderer.setSending(true);
  activeChatAbortController = new AbortController();

  store.addMessage({ role: "user", content: text });
  store.updateTitleFromPrompt(text);
  renderer.addBubble({ role: "user", text });
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
