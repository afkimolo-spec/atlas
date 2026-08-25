# Atlas Migration Guide

## Purpose

This document describes how to migrate the current operational Atlas installation to another Ubuntu machine.

The migration package preserves the current Atlas installation state and the external resources required to reconstruct it.

The snapshot includes:

- Atlas source code
- `.ai` architecture and persistent state
- Atlas memory and execution databases
- external Atlas runtime resources
- llama.cpp resources
- Atlas-related systemd services
- referenced environment files
- installed system package information
- Python and uv environment information
- Node/npm environment information
- network configuration information
- scheduled-task information
- runtime process information
- listening-port information
- Git state
- model inventory

Model weights are not copied. Their exact filenames and sizes are recorded in the model manifest.


## 1. Migration Package

The migration snapshot is located at:

    ~/workspace/atlas/migration/

The master migration manifest is:

    migration/MIGRATION_MANIFEST.txt

The captured-file manifest is:

    migration/manifest/captured-files.tsv

The integrity manifest is:

    migration/manifest/SHA256SUMS

The migration package is a snapshot. It does not replace or remove the
running Atlas installation.

## 2. External Runtime Resources

External Atlas resources captured from the source machine are located under:

    migration/external/opt/

The expected restoration mapping is:

    migration/external/opt/llama.cpp -> /opt/llama.cpp
    migration/external/opt/scripts    -> /opt/scripts

Restore these resources while preserving their permissions and ownership.

The source `/opt/models` directory is not copied.

## 3. Model Restoration

The source model inventory is recorded in:

    migration/manifest/models.manifest

The destination machine must provide the corresponding GGUF files under:

    /opt/models/

The model filenames recorded in the manifest should be treated as
authoritative for this migration.

Do not rename model files unless the corresponding Atlas and llama.cpp
configuration is updated.

## 4. Atlas Repository

Restore the complete Atlas project to:

    /home/administrator/workspace/atlas

The `.ai` directory is part of the operational state and must be preserved.

Do not replace an existing migrated `.ai` directory with an empty directory.

## 5. Python Environment

The source `.venv` is not copied because Python virtual environments contain
machine-specific paths.

Recreate it on the destination with:

    cd ~/workspace/atlas
    uv sync

Then:

    source .venv/bin/activate

The captured Python environment information is available under:

    migration/system/packages/python-environment.txt

## 6. System Dependencies

Installed Debian packages are recorded in:

    migration/system/packages/dpkg-packages.tsv

Manually installed packages are recorded in:

    migration/system/packages/apt-manual.txt

Snap packages, when present, are recorded in:

    migration/system/packages/snap-packages.txt

These files describe the source machine. They should be reviewed before
installation on a destination machine running a different Ubuntu release.

## 7. Systemd Services

Atlas/llama-related systemd service definitions are captured under:

    migration/system/systemd/

Service runtime information is captured under:

    migration/runtime/services/

The identified service units are listed in:

    migration/manifest/systemd.units

Restore service definitions into:

    /etc/systemd/system/

Then execute:

    sudo systemctl daemon-reload

Do not start services until their dependencies, models, paths and
configuration have been restored.

## 8. Environment Files

Environment files referenced by captured services are stored under:

    migration/system/environment/

Their original paths are listed in:

    migration/manifest/environment.files

Restore each captured environment file to its corresponding original path.

The captured files represent the operational configuration of the source
installation.

## 9. Persistent Atlas State

Atlas persistent state is located under:

    /home/administrator/workspace/atlas/.ai/

The migration inventory is:

    migration/manifest/ai-state.manifest

Database files are inventoried in:

    migration/manifest/database.manifest

Preserve these files when migrating the operational installation.

## 10. Execution and Session State

Atlas currently supports persistent:

- execution state
- stage state
- execution restoration
- session persistence
- retry state
- recovery state
- autonomous recovery

Existing persistent state should be preserved during migration.

Before resuming unfinished executions on a destination system, inspect the
restored execution records.

## 11. Network Configuration

Captured network information is stored under:

    migration/system/network/

This includes:

- IP configuration
- routing information
- hostname information

Runtime listening sockets are recorded under:

    migration/runtime/ports/

The known Atlas model-service architecture uses:

    8000  Embedding
    8001  Completion
    8002  Agent
    8003  Research

The captured runtime records should be used as the authoritative source for
the state of the machine at migration time.

## 12. Scheduled Tasks

Cron and system-timer information is stored under:

    migration/system/cron/

Review these records before recreating scheduled tasks.

Do not create duplicate scheduled tasks if they already exist on the
destination.

## 13. Runtime Diagnostics

Runtime process information is stored under:

    migration/runtime/processes/

Service information is stored under:

    migration/runtime/services/

Port information is stored under:

    migration/runtime/ports/

Captured process environment information is stored under:

    migration/runtime/environment/

These records describe the source machine at migration time and are useful
for reconstructing and troubleshooting the destination.

## 14. Git State

The captured Git state is:

    migration/manifest/git-state.txt

The tracked-file inventory is:

    migration/manifest/git-tracked-files.txt

Use these records to compare the migration snapshot against the source
repository state.

## 15. Integrity Verification

The migration package contains:

    migration/manifest/SHA256SUMS

From the Atlas root, verify the package with:

    cd ~/workspace/atlas
    sha256sum -c migration/manifest/SHA256SUMS

Every captured file should report `OK`.

Investigate any checksum mismatch before treating the package as an exact
migration snapshot.

## 16. Destination Validation

After restoration:

    cd ~/workspace/atlas
    source .venv/bin/activate

Verify the model services:

    ss -lntup | grep -E ':(8000|8001|8002|8003)\b'

Verify the relevant services:

    systemctl --no-pager --type=service | grep -Ei 'atlas|llama'

Verify the models:

    ls -lh /opt/models/

Verify llama.cpp:

    ls -lah /opt/llama.cpp/

Then run the Atlas validation scripts available under:

    scripts/

and the project tests under:

    tests/

At minimum, validate session persistence, persistent memory, execution
persistence, execution restoration, retry, recovery and autonomous recovery.

## 17. Migration Safety

The migration builder is non-destructive.

It does not:

- delete source files
- move source files
- stop Atlas services
- stop llama.cpp services
- modify `/opt/models`
- replace Atlas persistent state

The migration package is created alongside the running installation.

## 18. Source-of-Truth Order

When reconstructing the installation, use this order of authority:

1. Current Atlas source
2. `.ai` project state
3. migration manifest
4. captured systemd definitions
5. captured environment configuration
6. captured dependency information
7. captured runtime diagnostics
8. model inventory

The migration snapshot represents the operational state observed at the
time it was generated.

## 19. Final Migration Checklist

- [ ] Atlas repository restored
- [ ] `.ai` state restored
- [ ] persistent databases restored
- [ ] `/opt/llama.cpp` restored
- [ ] `/opt/scripts` restored
- [ ] required GGUF models restored
- [ ] system dependencies installed
- [ ] Python/uv environment recreated
- [ ] environment files restored
- [ ] systemd services restored
- [ ] systemd daemon reloaded
- [ ] network requirements verified
- [ ] required ports available
- [ ] model services operational
- [ ] Atlas tests pass
- [ ] persistent memory verified
- [ ] execution restoration verified
- [ ] autonomous recovery verified
- [ ] SHA-256 verification passes
