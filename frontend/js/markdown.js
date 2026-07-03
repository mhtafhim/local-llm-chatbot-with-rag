export function renderMarkdown(text) {
  const html = window.marked.parse(text || "");
  const wrapper = document.createElement("div");
  wrapper.innerHTML = html;

  wrapper.querySelectorAll("pre code").forEach((block) => {
    window.hljs.highlightElement(block);
    addCopyButton(block);
  });

  return wrapper.innerHTML;
}

function addCopyButton(block) {
  const pre = block.parentElement;
  const button = document.createElement("button");
  button.className = "copyBtn";
  button.textContent = "Copy";
  button.addEventListener("click", () => {
    navigator.clipboard.writeText(block.textContent);
    button.textContent = "Copied!";
    window.setTimeout(() => {
      button.textContent = "Copy";
    }, 1200);
  });

  pre.style.position = "relative";
  pre.appendChild(button);
}
