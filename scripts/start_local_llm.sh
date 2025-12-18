#!/bin/bash
set -euo pipefail
set -o pipefail

# Start a local OpenAI-compatible server backed by llama.cpp or similar.
# Reads configuration from .env (LOCAL_BASE_URL, LOCAL_MODEL, LOCAL_API_KEY, etc.).
# Requires the `llama-server` binary from llama.cpp to be installed and accessible on PATH.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Load environment if present (optional)
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
else
  echo "ℹ️  .env not found. Using defaults + CLI args (see .env.template)." >&2
fi

LLAMA_BIN="${LLAMA_BIN:-llama-server}"
MODEL_PATH="${MODEL_PATH:-${LOCAL_MODEL_PATH:-}}"
MODEL_ID="${LOCAL_MODEL:-gpt-oss-20b-mxfp4}"
PORT="${LOCAL_PORT:-8080}"
HOST="${LOCAL_HOST:-127.0.0.1}"
THREADS="${LLM_THREADS:-8}"
CONTEXT="${LLM_CONTEXT:-4096}"

# Allow passing -m/--model via CLI args if env not set
if [[ -z "$MODEL_PATH" ]]; then
  if printf '%s\n' "$*" | grep -Eq -- '(^|\s)(-m|--model)\s'; then
    echo "ℹ️  MODEL_PATH not set; using model path from CLI args (-m/--model)." >&2
  else
    echo "❌ MODEL_PATH/LOCAL_MODEL_PATH not set and no -m/--model provided. Set LOCAL_MODEL_PATH in .env or pass -m <model.gguf>." >&2
    exit 1
  fi
fi

if ! command -v "$LLAMA_BIN" >/dev/null 2>&1; then
  echo "❌ Unable to find llama-server binary. Install llama.cpp and ensure llama-server is on PATH." >&2
  exit 1
fi

LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/local_llm.log"

exec "$LLAMA_BIN" \
  ${MODEL_PATH:+-m "$MODEL_PATH"} \
  -hf "$MODEL_ID" \
  -fa \
  --host "$HOST" \
  --port "$PORT" \
  --ctx-size "$CONTEXT" \
  --threads "$THREADS" \
  --api-key "${LOCAL_API_KEY:-sk-local}" \
  --explain "Tatlam local OpenAI-compatible endpoint" \
  "$@" | tee -a "$LOG_FILE"
