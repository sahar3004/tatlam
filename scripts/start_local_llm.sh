#!/bin/bash
# start_local_llm.sh - Start the local LLM server with Metal GPU support
#
# Optimized for Apple Silicon (M1/M2/M3/M4 Pro)
# Includes automatic Metal detection and keep-alive functionality

set -e

# ============================================================================
# Configuration
# ============================================================================

MODEL_PATH="${MODEL_PATH:-models/llama-4-70b-instruct.gguf}"
MODEL_ALIAS="${MODEL_ALIAS:-llama-3.3-70b-instruct}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
N_CTX="${N_CTX:-8192}"
N_GPU_LAYERS="${N_GPU_LAYERS:-99}"
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
    echo ""

    # MPS (Metal Performance Shaders) optimization
    export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

    python3 -m llama_cpp.server \
        --model "$MODEL_PATH" \
        --n_gpu_layers "$N_GPU_LAYERS" \
        --n_ctx "$N_CTX" \
        --host "$HOST" \
        --port "$PORT" \
        --alias "$MODEL_ALIAS" \
        --flash_attn True
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
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --keep-alive, -k  Automatically restart server on crash"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  MODEL_PATH        Path to GGUF model file"
            echo "  MODEL_ALIAS       Model alias for API"
            echo "  HOST              Server host (default: 0.0.0.0)"
            echo "  PORT              Server port (default: 8080)"
            echo "  N_CTX             Context window size (default: 8192)"
            echo "  N_GPU_LAYERS      GPU layers to offload (default: 99)"
            echo "  RESTART_DELAY     Seconds before restart (default: 5)"
            exit 0
            ;;
        *)
            start_server
            ;;
    esac
}

main "$@"
