#!/usr/bin/env bash
set -euo pipefail

ROOT="${ATLAS_ROOT:-/home/administrator/workspace/atlas}"
DATABASE="${ATLAS_DATABASE:-$ROOT/.ai/memory/db/atlas.db}"
BACKUP_ROOT="${ATLAS_BACKUP_ROOT:-$ROOT/backups}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$BACKUP_ROOT/$TIMESTAMP"

mkdir -p "$TARGET"

if [ ! -f "$DATABASE" ]; then
    echo "Atlas database not found: $DATABASE" >&2
    exit 1
fi

sqlite3 "$DATABASE" ".backup '$TARGET/atlas.db'"

if [ -d "$ROOT/configs" ]; then
    cp -a "$ROOT/configs" "$TARGET/configs"
fi

if [ -f "$ROOT/pyproject.toml" ]; then
    cp "$ROOT/pyproject.toml" "$TARGET/"
fi

if [ -f "$ROOT/uv.lock" ]; then
    cp "$ROOT/uv.lock" "$TARGET/"
fi

printf '%s\n' "$TARGET"
