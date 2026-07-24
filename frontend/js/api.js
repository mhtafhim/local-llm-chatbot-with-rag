import { RAG_BACKEND } from "./config.js?v=4";

export async function getBackendStatus() {
  const response = await fetch(`${RAG_BACKEND}/`);
  if (!response.ok) throw new Error(`Backend status failed: ${response.status}`);
  return response.json();
}

export async function listDocuments() {
  const response = await fetch(`${RAG_BACKEND}/documents`);
  if (!response.ok) throw new Error(`Document list failed: ${response.status}`);
  return response.json();
}

export async function clearDocuments() {
  const response = await fetch(`${RAG_BACKEND}/clear`, { method: "POST" });
  if (!response.ok) throw new Error(`Clear failed: ${response.status}`);
  return response.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${RAG_BACKEND}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
  return response.json();
}

export async function analyzeUpload(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${RAG_BACKEND}/analyze-upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = `Analyze failed: ${response.status}`;
    try {
      const data = await response.json();
      if (data?.detail) message = data.detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(message);
  }

  return response.json();
}

export async function streamChat({
  messages,
  useRag,
  useWebSearch,
  useThinking,
  attachments,
  signal,
  onEvent,
}) {
  const response = await fetch(`${RAG_BACKEND}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal,
    body: JSON.stringify({
      messages,
      use_rag: useRag,
      use_web_search: useWebSearch,
      use_thinking: useThinking,
      attachments:
        attachments && attachments.length
          ? attachments.map(({ type, filename, content, mime_type }) => ({
              type,
              filename,
              content,
              mime_type,
            }))
          : undefined,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Request failed: ${response.status}`);
  }

  await readServerSentEvents(response.body, onEvent);
}

async function readServerSentEvents(body, onEvent) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();

    for (const line of lines) {
      const event = parseSseLine(line);
      if (event) onEvent(event);
    }
  }

  const finalEvent = parseSseLine(buffer);
  if (finalEvent) onEvent(finalEvent);
}

function parseSseLine(line) {
  const trimmed = line.trim();
  if (!trimmed.startsWith("data:")) return null;

  const payload = trimmed.slice(5).trim();
  if (!payload || payload === "[DONE]") return { type: "done" };

  try {
    return JSON.parse(payload);
  } catch {
    return null;
  }
}
