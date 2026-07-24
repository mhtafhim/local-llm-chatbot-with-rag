import { renderMarkdown } from "./markdown.js?v=4";
import { escapeHtml } from "./utils.js?v=4";

export class ChatRenderer {
  constructor(elements, handlers) {
    this.elements = elements;
    this.handlers = handlers;
  }

  renderSidebar(entries, activeChatId) {
    this.elements.chatList.innerHTML = "";

    entries.forEach((entry) => {
      const item = document.createElement("div");
      item.className = `chatItem${entry.id === activeChatId ? " active" : ""}`;
      item.dataset.chatId = entry.id;

      const title = document.createElement("span");
      title.textContent = entry.title;

      const deleteButton = document.createElement("span");
      deleteButton.className = "del";
      deleteButton.textContent = "x";
      deleteButton.dataset.deleteChatId = entry.id;

      item.append(title, deleteButton);
      this.elements.chatList.appendChild(item);
    });
  }

  renderMessages(messages) {
    this.elements.chat.innerHTML = "";
    messages.forEach((message) => {
      this.addBubble({
        role: message.role,
        text: message.content,
        sources: message.sources,
        thinking: message.thinking,
        webResults: message.webResults,
        attachments: message.attachments,
        scroll: false,
      });
    });
    this.scrollToBottom();
  }

  renderDocuments(documents) {
    this.elements.docList.innerHTML = "";

    if (!documents.length) {
      const empty = document.createElement("div");
      empty.className = "docListEmpty";
      empty.textContent = "No documents yet";
      this.elements.docList.appendChild(empty);
      return;
    }

    documents.forEach((documentName) => {
      const item = document.createElement("div");
      item.textContent = documentName;
      this.elements.docList.appendChild(item);
    });
  }

  renderDocumentsError() {
    this.elements.docList.innerHTML = "";
    const item = document.createElement("div");
    item.className = "docListError";
    item.textContent = "RAG backend not running";
    this.elements.docList.appendChild(item);
  }

  addBubble({
    role,
    text,
    sources = null,
    thinking = "",
    webResults = null,
    webStatus = "",
    attachments = null,
    scroll = true,
  }) {
    const row = document.createElement("div");
    row.className = `row ${role}`;

    const bubble = document.createElement("div");
    bubble.className = `bubble ${role}`;

    if (role === "user") {
      bubble.innerHTML = renderUserBubble(text, attachments);
    } else {
      bubble.innerHTML = renderAssistantBubble({ text, thinking, webResults, webStatus, sources });
    }

    row.appendChild(bubble);
    this.elements.chat.appendChild(row);
    if (scroll) this.scrollToBottom();
    return bubble;
  }

  refreshAssistantBubble(bubble, state) {
    bubble.innerHTML = renderAssistantBubble(state);
    this.scrollToBottom();
  }

  setSidebarOpen(isOpen) {
    this.elements.sidebar.classList.toggle("open", isOpen);
    this.elements.overlay.classList.toggle("show", isOpen);
  }

  toggleSidebar() {
    const isOpen = !this.elements.sidebar.classList.contains("open");
    this.setSidebarOpen(isOpen);
  }

  setSending(isSending) {
    this.elements.sendBtn.disabled = isSending;
    this.elements.stopBtn.hidden = !isSending;
  }

  setModelStatus(text) {
    this.elements.modelStatus.textContent = text;
  }

  scrollToBottom() {
    this.elements.chat.scrollTop = this.elements.chat.scrollHeight;
  }
}

function renderUserBubble(text, attachments) {
  const chips = (attachments || [])
    .map(
      (attachment) =>
        `<span class="attachmentChip">${attachment.type === "image" ? "🖼" : "📄"} ${escapeHtml(attachment.filename)}</span>`,
    )
    .join("");
  const chipRow = chips ? `<div class="attachmentChips">${chips}</div>` : "";
  return `${chipRow}${escapeHtml(text)}`;
}

function renderAssistantBubble({ text = "", thinking = "", webResults = null, webStatus = "", sources = null }) {
  let html = renderWebResults(webResults, webStatus);
  html += renderThinking(thinking);
  html += renderMarkdown(text);

  const wrapper = document.createElement("div");
  wrapper.innerHTML = html;

  if (sources?.length) {
    const sourceList = document.createElement("div");
    sourceList.className = "sources";
    sourceList.innerHTML = `Sources: ${sources.map((source) => `<span>${escapeHtml(source)}</span>`).join("")}`;
    wrapper.appendChild(sourceList);
  }

  return wrapper.innerHTML;
}

function renderThinking(text) {
  if (!text) return "";
  return `<details class="thinkingBox" open><summary>Thinking</summary><div class="thinkingContent">${escapeHtml(text)}</div></details>`;
}

function renderWebResults(results, status = "") {
  if (!status && !results?.length) return "";

  const rows = (results || [])
    .map(
      (result) => `
        <div class="webResult">
          <div class="webResultTitle">${escapeHtml(result.title || "Untitled")}</div>
          ${result.url ? `<div class="webResultUrl">${escapeHtml(result.url)}</div>` : ""}
          <div>${escapeHtml(result.snippet || "")}</div>
        </div>
      `,
    )
    .join("");

  return `<div class="webSearchBox"><strong>${escapeHtml(status || "Web search results")}</strong>${rows}</div>`;
}
