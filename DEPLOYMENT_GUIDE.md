# Atlas Deployment Guide

## 1. Prerequisites

Recommended target: Ubuntu Linux with sufficient CPU, RAM, and SSD storage for the selected local LLM models.

Required software:

- Git
- Python 3
- uv
- llama.cpp
- systemd

## 2. Restore Atlas

Place the repository at:

`/home/administrator/workspace/atlas`

Verify:

    cd ~/workspace/atlas
    git status

## 3. Restore External Runtime

The migration package contains copies of the external Atlas runtime resources.

Restore:

    migration/external/opt/llama.cpp -> /opt/llama.cpp
    migration/external/opt/scripts -> /opt/scripts

The restoration requires appropriate administrative privileges.

## 4. Restore Models

Do not expect model weights inside Git.

The required model inventory is:

    migration/manifest/models.manifest

Place the required GGUF files under:

    /opt/models

Verify filenames and sizes against the manifest.

## 5. Restore Python Environment

    cd ~/workspace/atlas
    uv sync
    source .venv/bin/activate

Verify:

    PYTHONPATH=src python -c "import atlas; print(\"Atlas import OK\")"

## 6. Restore Persistent State

Preserve the `.ai` directory exactly.

The primary database is:

    .ai/memory/db/atlas.db

## 7. Restore Services

Restore the captured systemd unit definitions from:

    migration/system/systemd/

Then execute:

    sudo systemctl daemon-reload

Enable/start the required units according to:

    migration/manifest/systemd.units

## 8. Verify Model Services

    ss -lntup | grep -E ":(8000|8001|8002|8003)\\b"

Expected services:

- 8000 embedding
- 8001 completion
- 8002 agent
- 8003 research

## 9. Verify Atlas

Run the project test suite after the environment and services are restored.

At minimum verify:

- session persistence
- persistent memory
- execution persistence
- execution restore
- autonomous execution
- autonomous recovery

## 10. Operational Recovery

If an Atlas process terminates unexpectedly, inspect the execution persistence database and service state before restarting work.

Captured operational information is available under `migration/runtime/`.

## 11. Troubleshooting

### Model endpoint unavailable

Check systemd status and listening ports.

### Atlas import failure

Verify `.venv`, run `uv sync`, activate the environment, and ensure `PYTHONPATH=src` is set when using the script-based test suite.

### Missing persistent state

Verify `.ai/` and `.ai/memory/db/atlas.db` were restored.

### Missing model

Compare `/opt/models` against `migration/manifest/models.manifest`.
