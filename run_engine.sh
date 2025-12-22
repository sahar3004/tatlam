#!/bin/bash
echo "🚀 Starting Qwen 2.5 on Apple M4 Pro (Metal/MPS)..."

# Kill old instances
killall llama-server 2>/dev/null

# Run Server (Background)
/opt/homebrew/bin/llama-server \
  -m /Users/sahar.miterani/models/Qwen2.5-32B-Instruct-Q5_K_M.gguf \
  --port 8080 \
  -ngl 99 \
  -c 16384 \
  --batch-size 512 \
  --threads 8 \
  --parallel 4 \
  --ctx-size 16384 \
  --nobrowser > llama.log 2>&1 &

echo "⏳ Waiting for Model to Load..."
sleep 5
echo "✅ Model is running in background. Logs in llama.log"
