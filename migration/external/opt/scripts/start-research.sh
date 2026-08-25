#!/bin/bash
set -euo pipefail

exec /opt/llama.cpp/build/bin/llama-server \
    --model /opt/models/qwen2.5-coder-32b-instruct-q2_k.gguf \
    --host 0.0.0.0 \
    --port 8003 \
    --ctx-size 16384 \
    --threads 32 \
    --threads-batch 32 \
    --parallel 1 \
    --batch-size 2048 \
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
    --reasoning auto
