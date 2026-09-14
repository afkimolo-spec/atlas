#!/usr/bin/env bash
set -euo pipefail

ROOT="${ATLAS_ROOT:-/home/administrator/workspace/atlas}"
DATABASE="${ATLAS_DATABASE:-$ROOT/.ai/memory/db/atlas.db}"

SOURCE="${1:-}"

if [ -z "$SOURCE" ]; then
    echo "Usage: restore_atlas.sh <backup-directory-or-database>" >&2
    exit 2
fi

if [ -d "$SOURCE" ]; then
    SOURCE="$SOURCE/atlas.db"
fi

if [ ! -f "$SOURCE" ]; then
    echo "Backup database not found: $SOURCE" >&2
    exit 1
fi

mkdir -p "$(dirname "$DATABASE")"

if [ -f "$DATABASE" ]; then
    cp "$DATABASE" "$DATABASE.pre-restore"
fi

sqlite3 "$SOURCE" ".restore '$DATABASE'"

sqlite3 "$DATABASE" "PRAGMA integrity_check;" |
    grep -qx "ok"

echo "Atlas database restored: $DATABASE"
