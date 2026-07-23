FROM python:3.12.13-alpine3.23@sha256:601d3d3797e90e2534782e69c85fafb7971b43f24c7b1b079b7e48dd435e458d AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /build

COPY requirements.lock ./
RUN python -m venv "${VIRTUAL_ENV}" \
    && python -m pip install \
        --no-cache-dir \
        --require-hashes \
        --only-binary=:all: \
        --requirement requirements.lock

FROM python:3.12.13-alpine3.23@sha256:601d3d3797e90e2534782e69c85fafb7971b43f24c7b1b079b7e48dd435e458d AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    WORKDIR=/app

WORKDIR ${WORKDIR}

COPY --from=dependencies /opt/venv /opt/venv
COPY . .

# Compila los estáticos (admin de Django) dentro de la imagen; WhiteNoise los
# sirve bajo gunicorn en el perfil pilot. La SECRET_KEY de placeholder solo
# existe durante este paso de build (collectstatic no usa la clave ni la BD).
RUN READ_DOT_ENV_FILE=False DEBUG=True \
    SECRET_KEY=build-only-collectstatic-placeholder \
    python manage.py collectstatic --noinput

# Usuario no root para seguridad
RUN addgroup -S vimeruser \
    && adduser -S -D -H -s /sbin/nologin -G vimeruser vimeruser \
    && mkdir -p /app/data /app/media /app/staticfiles \
    && chmod 0555 /app/deploy/entrypoint.sh /app/deploy/scheduler.sh \
    && chown -R vimeruser:vimeruser /app/data /app/media /app/staticfiles \
    && chmod -R go-w /app
USER vimeruser

EXPOSE 8000

ENTRYPOINT ["/app/deploy/entrypoint.sh"]
HEALTHCHECK --interval=30s --timeout=6s --start-period=45s --retries=3 \
    CMD ["python", "/app/deploy/container_healthcheck.py"]
