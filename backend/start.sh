#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

export LLM_PROVIDER="${LLM_PROVIDER:-ollama}"
export OLLAMA_BASE="${OLLAMA_BASE:-http://localhost:11434}"
export OLLAMA_CHAT_MODEL="${OLLAMA_CHAT_MODEL:-gemma4:e4b}"
export OLLAMA_EMBED_MODEL="${OLLAMA_EMBED_MODEL:-nomic-embed-text}"
export LMSTUDIO_BASE="${LMSTUDIO_BASE:-http://localhost:1234/v1}"

echo "Starting RAG backend on http://0.0.0.0:8001"
echo "Provider: $LLM_PROVIDER"
if [ "$LLM_PROVIDER" = "ollama" ]; then
  echo "Ollama: $OLLAMA_BASE"
  echo "Chat model: $OLLAMA_CHAT_MODEL"
  echo "Embedding model: $OLLAMA_EMBED_MODEL"
else
  echo "LM Studio: $LMSTUDIO_BASE"
  echo "Chat model: ${LMSTUDIO_CHAT_MODEL:-auto-detect}"
  echo "Embedding model: ${LMSTUDIO_EMBED_MODEL:-text-embedding-nomic-embed-text-v1.5}"
fi
echo

exec uvicorn main:app --host 0.0.0.0 --port 8001
