#!/usr/bin/env bash
# Manual backup of the production database (Supabase free plan has no automatic backups).
# Usage:  DATABASE_URL='postgresql://…' scripts/backup_db.sh [output-dir]
# The dump contains everyone's data. Keep it on your own machine, never commit or share it.
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to the production connection string}"
command -v pg_dump >/dev/null || { echo "pg_dump not found. Install PostgreSQL client tools first (macOS: brew install libpq)." >&2; exit 1; }

dir="${1:-$HOME/nomica-backups}"
mkdir -p "$dir"
chmod 700 "$dir"
file="$dir/nomica-$(date +%Y%m%d-%H%M%S).dump"

pg_dump --format=custom --no-owner --no-privileges --file="$file" "$DATABASE_URL"
chmod 600 "$file"
echo "Backup written: $file ($(du -h "$file" | cut -f1))"
echo "Verify it lists tables:  pg_restore --list '$file' | head"
echo "Older backups in $dir (delete the ones you no longer need):"
ls -1t "$dir" | sed -n '2,$p' | head -20
