import { STORAGE_KEYS } from "./config.js";

export class ChatStore {
  constructor(storage = window.localStorage) {
    this.storage = storage;
    this.chats = this.readChats();
    this.activeChatId = this.storage.getItem(STORAGE_KEYS.activeChat);

    if (!this.activeChatId || !this.chats[this.activeChatId]) {
      this.activeChatId = this.createChat();
    }
  }

  get activeChat() {
    return this.chats[this.activeChatId];
  }

  createChat() {
    const id = `chat_${Date.now()}`;
    this.chats[id] = { title: "New Chat", messages: [] };
    this.activeChatId = id;
    this.save();
    return id;
  }

  setActiveChat(id) {
    if (!this.chats[id]) return;
    this.activeChatId = id;
    this.save();
  }

  deleteChat(id) {
    delete this.chats[id];

    if (this.activeChatId === id) {
      const [nextId] = Object.keys(this.chats);
      this.activeChatId = nextId || this.createChat();
    }

    this.save();
  }

  addMessage(message) {
    this.activeChat.messages.push(message);
    this.save();
  }

  updateTitleFromPrompt(prompt) {
    if (this.activeChat.title !== "New Chat") return;
    this.activeChat.title = prompt.slice(0, 30) + (prompt.length > 30 ? "..." : "");
    this.save();
  }

  listChatEntries() {
    return Object.keys(this.chats)
      .reverse()
      .map((id) => ({ id, ...this.chats[id] }));
  }

  save() {
    this.storage.setItem(STORAGE_KEYS.chats, JSON.stringify(this.chats));
    this.storage.setItem(STORAGE_KEYS.activeChat, this.activeChatId);
  }

  readChats() {
    try {
      return JSON.parse(this.storage.getItem(STORAGE_KEYS.chats) || "{}");
    } catch {
      return {};
    }
  }
}
