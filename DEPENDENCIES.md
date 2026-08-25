# Atlas Dependencies

## Python

Atlas uses Python and uv.

Authoritative dependency files:

- pyproject.toml
- uv.lock

Verify:

    python3 --version
    uv --version

Recreate the environment:

    cd ~/workspace/atlas
    uv sync
    source .venv/bin/activate

## Python Runtime

The current operational Python environment is documented in:

    migration/system/packages/python-environment.txt

The installed package inventory is:

    migration/system/packages/dpkg-packages.tsv

Manually installed APT packages are:

    migration/system/packages/apt-manual.txt

## Node.js

Node.js/npm information is captured in:

    migration/system/packages/node-environment.txt

Node.js is required only where project tooling explicitly depends on it.

## llama.cpp

Atlas uses llama.cpp for local model inference.

Runtime location:

    /opt/llama.cpp

Migration copy:

    migration/external/opt/llama.cpp

## Models

Atlas uses local GGUF models.

Model location:

    /opt/models

The migration package does not contain model weights.

Required model filenames and sizes are recorded in:

    migration/manifest/models.manifest

Models must be restored to:

    /opt/models

## Atlas Runtime Scripts

Operational scripts are located at:

    /opt/scripts

Migration copy:

    migration/external/opt/scripts

## Local Inference Endpoints

Embedding service:

    http://localhost:8000

Fast completion:

    http://localhost:8001/v1

Agent:

    http://localhost:8002/v1

Research:

    http://localhost:8003/v1

## Persistent Storage

Atlas persistent state is stored under:

    .ai/

The primary persistent database is:

    .ai/memory/db/atlas.db

The migration state inventory is:

    migration/manifest/ai-state.manifest

## System Services

Atlas/llama-related systemd definitions are captured under:

    migration/system/systemd/

The service inventory is:

    migration/manifest/systemd.units

## Reproducibility

A clean installation requires:

1. Ubuntu Linux
2. Required system packages
3. Python
4. uv
5. Atlas source
6. Python dependencies from uv.lock
7. llama.cpp
8. Atlas runtime scripts
9. Required GGUF models
10. Captured systemd configuration
11. Required environment configuration
12. Persistent .ai state

The authoritative restoration procedure is:

    MIGRATION_GUIDE.md
