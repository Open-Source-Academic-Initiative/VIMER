#!/bin/sh
set -eu

profile="${1:-}"
backup_directory="${2:-}"
confirmation="${3:-}"
if [ "$profile" != "pilot" ] && [ "$profile" != "production" ]; then
    echo "usage: restore.sh {pilot|production} BACKUP_DIRECTORY --confirm" >&2
    exit 2
fi
if [ "$confirmation" != "--confirm" ]; then
    echo "Restore is destructive; rerun with the exact --confirm flag." >&2
    exit 2
fi
if [ -z "$backup_directory" ] || [ "$backup_directory" = "/" ] || [ ! -d "$backup_directory" ]; then
    echo "A valid, specific backup directory is required." >&2
    exit 2
fi

(
    cd "$backup_directory"
    sha256sum --check MANIFEST.sha256
)
if [ -f "$backup_directory/media.tar.gz" ]; then
    python3 deploy/ops/validate_media_archive.py \
        "$backup_directory/media.tar.gz"
fi

compose_command="${COMPOSE_COMMAND:-docker-compose}"
compose_file="docker-compose.${profile}.yml"
running_web="$("$compose_command" -f "$compose_file" ps -q web 2>/dev/null || true)"
running_scheduler="$("$compose_command" -f "$compose_file" ps -q scheduler 2>/dev/null || true)"
if [ -n "$running_web" ] || [ -n "$running_scheduler" ]; then
    echo "Stop the web and scheduler services before restoring data." >&2
    exit 1
fi

if [ "$profile" = "pilot" ]; then
    sqlite_path="${VIMER_SQLITE_PATH:-./data/db.sqlite3}"
    python3 deploy/ops/sqlite_restore.py \
        "$backup_directory/database.sqlite3" \
        "$sqlite_path"
else
    "$compose_command" -f docker-compose.production.yml exec -T db \
        pg_restore \
        --clean \
        --if-exists \
        --exit-on-error \
        --no-owner \
        --single-transaction \
        --username="${POSTGRES_USER:-vimer}" \
        --dbname="${POSTGRES_DB:-vimer}" \
        < "$backup_directory/database.dump"
fi

if [ "${RESTORE_MEDIA:-False}" = "True" ] && [ -f "$backup_directory/media.tar.gz" ]; then
    if [ "$profile" = "production" ]; then
        preserved_media="$backup_directory/media.pre-restore-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
        "$compose_command" -f docker-compose.production.yml run \
            --rm \
            --no-deps \
            -T \
            --entrypoint tar \
            web \
            -C /app/media -czf - . \
            > "$preserved_media"
        "$compose_command" -f docker-compose.production.yml run \
            --rm \
            --no-deps \
            -T \
            --entrypoint sh \
            web \
            -c 'find /app/media -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +'
        "$compose_command" -f docker-compose.production.yml run \
            --rm \
            --no-deps \
            -T \
            --entrypoint tar \
            web \
            -C /app/media -xzf - \
            < "$backup_directory/media.tar.gz"
        echo "Previous production media preserved at $preserved_media"
    else
        media_directory="${VIMER_MEDIA_DIR:-./media}"
        if [ "$media_directory" = "/" ] || [ -z "$media_directory" ]; then
            echo "Unsafe media restore target." >&2
            exit 2
        fi
        if [ -d "$media_directory" ]; then
            preserved_media="${media_directory%/}.pre-restore-$(date -u +%Y%m%dT%H%M%SZ)"
            mv "$media_directory" "$preserved_media"
            echo "Previous media preserved at $preserved_media"
        fi
        mkdir -p "$media_directory"
        tar -C "$media_directory" -xzf "$backup_directory/media.tar.gz"
    fi
fi

echo "Restore completed. Run checks and smoke tests before starting web."
