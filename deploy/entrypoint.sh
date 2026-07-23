#!/bin/sh
set -eu

profile="${DEPLOYMENT_PROFILE:-pilot}"

if [ "$profile" = "production" ]; then
    python manage.py check --deploy
else
    python manage.py check
fi

python -m deploy.wait_for_database
if [ "${RUN_STARTUP_TASKS:-True}" = "True" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

if [ "$#" -eq 0 ]; then
    set -- gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-3}" \
        --threads "${GUNICORN_THREADS:-1}" \
        --timeout "${GUNICORN_TIMEOUT:-60}" \
        --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
        --no-control-socket \
        --access-logfile - \
        --error-logfile - \
        --capture-output
fi

exec "$@"
