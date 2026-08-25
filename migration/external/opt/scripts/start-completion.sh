#!/bin/bash
set -euo pipefail

exec /opt/llama.cpp/build/bin/llama-server \
    --model /opt/models/qwen2.5-coder-7b-instruct-q8_0.gguf \
    --host 0.0.0.0 \
    --port 8001 \
    --ctx-size 8192 \
    --threads 16 \
    --threads-batch 32 \
    --parallel 2 \
    --batch-size 1024 \
    --ubatch-size 512 \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --flash-attn on \
    --numa distribute \
    --mlock \
    --metrics \
    --slots \
    --cache-prompt \
    --cont-batching \
    --poll 0 \
    --prio 2 \
    --reasoning off
