#!/bin/bash
set -euo pipefail
set -o pipefail

# Start a local OpenAI-compatible server backed by llama.cpp or similar.
# Reads configuration from .env (LOCAL_BASE_URL, LOCAL_MODEL, LOCAL_API_KEY, etc.).
# Requires the `llama-server` binary from llama.cpp to be installed and accessible on PATH.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f .env ]]; then
  echo "⚠️  .env not found. Create one from .env.template first." >&2
  exit 1
fi

set -a
source .env
set +a

LLAMA_BIN="${LLAMA_BIN:-llama-server}"
MODEL_PATH="${MODEL_PATH:-${LOCAL_MODEL_PATH:-}}"
MODEL_ID="${LOCAL_MODEL:-gpt-oss-20b-mxfp4}"
PORT="${LOCAL_PORT:-8080}"
HOST="${LOCAL_HOST:-127.0.0.1}"
THREADS="${LLM_THREADS:-8}"
CONTEXT="${LLM_CONTEXT:-4096}"

if [[ -z "$MODEL_PATH" ]]; then
  echo "⚠️  MODEL_PATH or LOCAL_MODEL_PATH must point to a GGUF model file." >&2
  exit 1
fi

if ! command -v "$LLAMA_BIN" >/dev/null 2>&1; then
  echo "❌ Unable to find llama-server binary. Install llama.cpp and ensure llama-server is on PATH." >&2
  exit 1
fi

LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/local_llm.log"

exec "$LLAMA_BIN" \
  -m "$MODEL_PATH" \
  -hf "$MODEL_ID" \
  -fa \
  --host "$HOST" \
  --port "$PORT" \
  --ctx-size "$CONTEXT" \
  --threads "$THREADS" \
  --api-key "${LOCAL_API_KEY:-sk-local}" \
  --explain "Tatlam local OpenAI-compatible endpoint" \
  "$@" | tee -a "$LOG_FILE"
