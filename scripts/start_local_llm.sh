#!/bin/bash
# start_local_llm.sh - Start the local LLM server with Metal GPU support
#
# Optimized for Apple Silicon M4 Pro (48GB RAM)
# Includes hardware parallelism for maximum throughput
# Includes automatic Metal detection and keep-alive functionality

set -e

# ============================================================================
# Configuration
# ============================================================================

# Load MODEL_PATH from .env if available
if [[ -f .env ]]; then
    # shellcheck disable=SC1091
    source <(grep -E '^LOCAL_MODEL_PATH=' .env | sed 's/^/export /')
fi

# Use LOCAL_MODEL_PATH from .env or fall back to argument/default
MODEL_PATH="${LOCAL_MODEL_PATH:-${1:-}}"
if [[ -z "$MODEL_PATH" ]]; then
    echo "❌ Error: MODEL_PATH not defined"
    echo "   Set LOCAL_MODEL_PATH in .env or pass as argument:"
    echo "   $0 /path/to/model.gguf"
    exit 1
fi

MODEL_ALIAS="${MODEL_ALIAS:-llama-3.3-70b-instruct}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
N_CTX="${N_CTX:-8192}"
N_GPU_LAYERS="${N_GPU_LAYERS:--1}"
N_PARALLEL="${N_PARALLEL:-8}"
BATCH_SIZE="${BATCH_SIZE:-512}"
RESTART_DELAY="${RESTART_DELAY:-5}"

# ============================================================================
# Metal GPU Support Detection
# ============================================================================

detect_metal_support() {
    echo "🔍 Detecting hardware..."

    # Check if running on macOS arm64 (Apple Silicon)
    if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
        echo "✅ Apple Silicon detected (M-series chip)"

        # Check if llama-cpp-python has Metal support
        if python3 -c "import llama_cpp; print(getattr(llama_cpp.llama_cpp, 'GGML_USE_METAL', False))" 2>/dev/null | grep -q "True"; then
            echo "✅ Metal GPU support is enabled"
            return 0
        else
            echo "⚠️  Metal GPU support NOT detected in llama-cpp-python"
            echo "   Reinstalling with Metal support..."
            install_metal_support
            return $?
        fi
    else
        echo "ℹ️  Not running on Apple Silicon, skipping Metal check"
        return 0
    fi
}

install_metal_support() {
    echo "📦 Installing llama-cpp-python with Metal support..."

    # Set environment variables for Metal compilation
    export CMAKE_ARGS="-DGGML_METAL=on"

    # Force reinstall without cache
    if pip install --force-reinstall --no-cache-dir llama-cpp-python; then
        echo "✅ llama-cpp-python installed with Metal support"
        return 0
    else
        echo "❌ Failed to install llama-cpp-python with Metal support"
        echo "   Try running manually:"
        echo "   CMAKE_ARGS=\"-DGGML_METAL=on\" pip install --force-reinstall --no-cache-dir llama-cpp-python"
        return 1
    fi
}

# ============================================================================
# Server Launch with Keep-Alive
# ============================================================================

start_server() {
    echo ""
    echo "🚀 Starting Local LLM Server"
    echo "   Model: $MODEL_PATH"
    echo "   Alias: $MODEL_ALIAS"
    echo "   Host: $HOST:$PORT"
    echo "   Context: $N_CTX tokens"
    echo "   GPU Layers: $N_GPU_LAYERS"
    echo "   Parallelism: 8 concurrent requests"
    echo "   Batch Size: 512"
    echo ""

    # MPS (Metal Performance Shaders) optimization
    export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

    python3 -m llama_cpp.server \
        --model "$MODEL_PATH" \
        --n_gpu_layers -1 \
        --n_ctx 8192 \
        --n_parallel 8 \
        --batch_size 512 \
        --host 0.0.0.0 \
        --port 8000 \
        --alias "$MODEL_ALIAS"
}

keep_alive() {
    echo "♻️  Keep-alive mode enabled. Server will restart on crash."
    echo "   Press Ctrl+C to stop."
    echo ""

    while true; do
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting server..."
        start_server || true

        echo ""
        echo "⚠️  Server exited. Restarting in ${RESTART_DELAY}s..."
        echo "   Press Ctrl+C to stop."
        sleep "$RESTART_DELAY"
    done
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
    echo "========================================"
    echo "  TATLAM Local LLM Server Launcher"
    echo "  Optimized for M4 Pro with Metal GPU"
    echo "========================================"
    echo ""

    # Check model file exists
    if [[ ! -f "$MODEL_PATH" ]]; then
        echo "❌ Model file not found: $MODEL_PATH"
        echo "   Please download the model first."
        exit 1
    fi

    # Detect and enable Metal support
    detect_metal_support

    # Parse arguments
    case "${1:-}" in
        --keep-alive|-k)
            keep_alive
            ;;
        --help|-h)
            echo "Usage: $0 [MODEL_PATH] [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --keep-alive, -k  Automatically restart server on crash"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  LOCAL_MODEL_PATH  Path to GGUF model file (required)"
            echo "  MODEL_ALIAS       Model alias for API"
            echo "  HOST              Server host (default: 0.0.0.0)"
            echo "  PORT              Server port (default: 8000)"
            echo "  N_CTX             Context window size (default: 8192)"
            echo "  N_GPU_LAYERS      GPU layers to offload (default: -1 = all)"
            echo "  N_PARALLEL        Concurrent request slots (default: 8)"
            echo "  BATCH_SIZE        Batch size for prompt processing (default: 512)"
            echo "  RESTART_DELAY     Seconds before restart (default: 5)"
            echo ""
            echo "Hardware Optimization (M4 Pro):"
            echo "  -1 GPU layers = offload all layers to Metal"
            echo "  8 parallel slots = handle 8 concurrent requests"
            echo "  512 batch size = optimal for 48GB unified memory"
            exit 0
            ;;
        *)
            start_server
            ;;
    esac
}

main "$@"
