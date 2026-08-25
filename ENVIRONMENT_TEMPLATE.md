# Atlas Environment Template

This document defines the environment required to reconstruct the current
Atlas installation.

## Host

OS: Ubuntu Linux
Architecture: x86_64
Atlas root: /home/administrator/workspace/atlas

## Python

Atlas uses Python and uv for Python environment and dependency management.

Authoritative files:

- pyproject.toml
- uv.lock

Verify:

python3 --version
uv --version

Recreate:

cd ~/workspace/atlas
uv sync
source .venv/bin/activate

## Local Model Services

Embedding:
http://localhost:8000

Fast completion:
http://localhost:8001/v1

Agent:
http://localhost:8002/v1

Research:
http://localhost:8003/v1

## Models

Models are maintained outside the Git repository under:

/opt/models

The exact required model files are recorded in:

migration/manifest/models.manifest

GGUF model weights are not included in the migration package.

## llama.cpp

Required runtime:

/opt/llama.cpp

The migration copy is located at:

migration/external/opt/llama.cpp

## Atlas Runtime Scripts

Required runtime scripts:

/opt/scripts

The migration copy is located at:

migration/external/opt/scripts

## Persistent Atlas State

Atlas persistent state:

/home/administrator/workspace/atlas/.ai

The migration package contains the corresponding state inventory:

migration/manifest/ai-state.manifest

Persistent database:

/home/administrator/workspace/atlas/.ai/memory/db/atlas.db

## System Services

Atlas/llama-related service definitions are captured under:

migration/system/systemd/

The corresponding service inventory is:

migration/manifest/systemd.units

## Environment Files

Environment files referenced by captured services are stored under:

migration/system/environment/

The inventory is:

migration/manifest/environment.files

## System Dependencies

Installed Debian packages:

migration/system/packages/dpkg-packages.tsv

Manually installed packages:

migration/system/packages/apt-manual.txt

Python environment information:

migration/system/packages/python-environment.txt

Node/npm information:

migration/system/packages/node-environment.txt

## Runtime Information

Process information:

migration/runtime/processes/

Service information:

migration/runtime/services/

Listening ports:

migration/runtime/ports/

Runtime environment information:

migration/runtime/environment/

## Network Information

Captured network configuration is under:

migration/system/network/

## Scheduled Tasks

Captured scheduled-task information is under:

migration/system/cron/

## Restoration Order

A clean machine should be restored in this order:

1. Provision Ubuntu.
2. Install required system packages.
3. Install Python and uv.
4. Restore the Atlas repository.
5. Run uv sync.
6. Restore /opt/llama.cpp.
7. Restore /opt/scripts.
8. Restore the required models into /opt/models.
9. Restore service definitions.
10. Restore referenced environment configuration.
11. Restore .ai persistent state.
12. Enable and start the required services.
13. Verify ports and model endpoints.
14. Run the Atlas test suite.
15. Verify execution, persistence, recovery, and workflow functionality.

The authoritative migration procedure is documented in MIGRATION_GUIDE.md.
