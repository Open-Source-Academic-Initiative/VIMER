#!/bin/sh
set -eu

profile="${1:-}"
destination="${2:-}"
if [ "$profile" != "pilot" ] && [ "$profile" != "production" ]; then
    echo "usage: backup.sh {pilot|production} DESTINATION_DIRECTORY" >&2
    exit 2
fi
if [ -z "$destination" ] || [ "$destination" = "/" ]; then
    echo "A specific backup destination is required." >&2
    exit 2
fi
if [ "${VIMER_BACKUP_WRITES_QUIESCED:-False}" != "True" ]; then
    echo "Stop or quiesce web and scheduler, then set VIMER_BACKUP_WRITES_QUIESCED=True." >&2
    exit 2
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_directory="${destination%/}/vimer-${profile}-${timestamp}"
mkdir -p "$destination"
umask 077
mkdir "$backup_directory"

if [ "$profile" = "pilot" ]; then
    sqlite_path="${VIMER_SQLITE_PATH:-./data/db.sqlite3}"
    python3 deploy/ops/sqlite_backup.py \
        "$sqlite_path" \
        "$backup_directory/database.sqlite3"
else
    compose_command="${COMPOSE_COMMAND:-docker-compose}"
    "$compose_command" -f docker-compose.production.yml exec -T db \
        pg_dump \
        --format=custom \
        --no-owner \
        --username="${POSTGRES_USER:-vimer}" \
        --dbname="${POSTGRES_DB:-vimer}" \
        > "$backup_directory/database.dump"
fi

if [ "$profile" = "production" ]; then
    compose_command="${COMPOSE_COMMAND:-docker-compose}"
    "$compose_command" -f docker-compose.production.yml run \
        --rm \
        --no-deps \
        -T \
        --entrypoint tar \
        web \
        -C /app/media -czf - . \
        > "$backup_directory/media.tar.gz"
else
    media_directory="${VIMER_MEDIA_DIR:-./media}"
    if [ -d "$media_directory" ]; then
        tar -C "$media_directory" -czf "$backup_directory/media.tar.gz" .
    fi
fi

(
    cd "$backup_directory"
    if [ -f media.tar.gz ]; then
        sha256sum database.* media.tar.gz
    else
        sha256sum database.*
    fi > MANIFEST.sha256
)

echo "Backup created at $backup_directory"
