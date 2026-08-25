#!/bin/bash
set -euo pipefail

exec /opt/llama.cpp/build/bin/llama-server \
    --model /opt/models/nomic-embed-text-v1.5-Q8_0.gguf \
    --embeddings \
    --pooling mean \
    --host 0.0.0.0 \
    --port 8000 \
    --ctx-size 8192 \
    --threads 16 \
    --threads-batch 16 \
    --batch-size 2048 \
    --ubatch-size 512 \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --numa distribute \
    --mlock \
    --metrics \
    --slots \
    --cont-batching
