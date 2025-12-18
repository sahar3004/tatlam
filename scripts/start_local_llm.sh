#!/bin/bash
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
python3 -m llama_cpp.server --model models/llama-4-70b-instruct.gguf --n_gpu_layers 99 --n_ctx 8192 --host 0.0.0.0 --port 8080 --alias llama-3.3-70b-instruct --flash_attn True
