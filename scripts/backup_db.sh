#!/usr/bin/env bash
#
# Nightly PostgreSQL snapshot for TalaMala.
#
# Credentials come from the project's .env so they live in exactly one place.
# Dumps in pg_dump's custom format (-Fc): compressed, and pg_restore can pull
# a single table out of it instead of forcing an all-or-nothing restore.
#
#   ./scripts/backup_db.sh              # write a snapshot
#   ./scripts/backup_db.sh --list       # show what is on disk
#
# Cron (03:00 every night):
#   0 3 * * * /path/to/talamala_v4/scripts/backup_db.sh >> /var/log/talamala-backup.log 2>&1
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$PROJECT_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/talamala}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
LOCK_FILE="/tmp/talamala-backup.lock"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { log "ERROR: $*"; exit 1; }

# --- credentials ---------------------------------------------------------
[[ -f "$ENV_FILE" ]] || die "env file not found: $ENV_FILE"

get_env() {
    # Last assignment wins, strips quotes and inline whitespace.
    grep -E "^${1}=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//' -e 's/[[:space:]]*$//'
}

DB_HOST="$(get_env DB_HOST)"; DB_HOST="${DB_HOST:-localhost}"
DB_PORT="$(get_env DB_PORT)"; DB_PORT="${DB_PORT:-5432}"
DB_NAME="$(get_env DB_NAME)"
DB_USER="$(get_env DB_USER)"
DB_PASSWORD="$(get_env DB_PASSWORD)"

[[ -n "$DB_NAME" ]] || die "DB_NAME missing from $ENV_FILE"
[[ -n "$DB_USER" ]] || die "DB_USER missing from $ENV_FILE"

# --- --list --------------------------------------------------------------
if [[ "${1:-}" == "--list" ]]; then
    log "backups in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/*.dump 2>/dev/null || log "  (none yet)"
    exit 0
fi

command -v pg_dump >/dev/null || die "pg_dump not installed (apt install postgresql-client)"

# --- one run at a time ---------------------------------------------------
exec 9>"$LOCK_FILE"
flock -n 9 || die "another backup is already running"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

STAMP="$(date '+%Y-%m-%d_%H%M')"
TARGET="$BACKUP_DIR/${DB_NAME}_${STAMP}.dump"
TMP="$TARGET.part"

cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

# --- dump ----------------------------------------------------------------
log "dumping $DB_NAME from $DB_HOST:$DB_PORT ..."
export PGPASSWORD="$DB_PASSWORD"

if ! pg_dump --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
             --dbname="$DB_NAME" --format=custom --compress=9 \
             --no-owner --no-privileges --file="$TMP" 2>&1; then
    die "pg_dump failed — no snapshot written"
fi
unset PGPASSWORD

# A dump that cannot be listed is not a backup. Catch corruption now, not
# on the night we actually need to restore.
pg_restore --list "$TMP" >/dev/null 2>&1 || die "dump is unreadable — discarding"

TABLES="$(pg_restore --list "$TMP" 2>/dev/null | grep -c 'TABLE DATA' || true)"
[[ "$TABLES" -gt 0 ]] || die "dump contains no table data — discarding"

mv "$TMP" "$TARGET"
chmod 600 "$TARGET"
trap - EXIT

log "OK: $TARGET ($(du -h "$TARGET" | cut -f1), $TABLES tables)"

# --- retention -----------------------------------------------------------
DELETED="$(find "$BACKUP_DIR" -name "${DB_NAME}_*.dump" -type f -mtime "+$RETENTION_DAYS" -print -delete | wc -l)"
[[ "$DELETED" -gt 0 ]] && log "pruned $DELETED snapshot(s) older than $RETENTION_DAYS days"

KEPT="$(find "$BACKUP_DIR" -name "${DB_NAME}_*.dump" -type f | wc -l)"
log "done — $KEPT snapshot(s) on disk, $(df -h "$BACKUP_DIR" | awk 'NR==2{print $4}') free"
