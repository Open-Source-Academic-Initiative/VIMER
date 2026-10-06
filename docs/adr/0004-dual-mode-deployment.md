# ADR 0004: Dual-Mode Deployment for Pilot and Production

## Status

Accepted

## Context

The first official release of VIMER is scoped as a closed pilot whose URL is distributed only to invited participants, but the same codebase must remain capable of a production-grade deployment posture later, without a rewrite or a divergent branch.

El perfil diferencia la topología HTTP/TLS y sus controles de seguridad.
El motor de persistencia se selecciona de manera independiente.

The application server itself is not a point of variation: gunicorn was already adopted in `Dockerfile` and `docker-compose.yml` to replace Django's development server, and that decision is preserved across both modes.

## Decision

VIMER will ship a single codebase that supports two deployment profiles through configuration only:

- `DEPLOYMENT_PROFILE=pilot`
  - Persistencia: SQLite por defecto o PostgreSQL mediante `DATABASE_URL`.
  - serving topology: gunicorn exposed directly behind whatever TLS terminator the operator chooses, or unencrypted when bound to a closed network
  - intended for the controlled pilot phase
- `DEPLOYMENT_PROFILE=production`
  - Persistencia: SQLite o PostgreSQL mediante `DATABASE_URL`; MariaDB no está certificado para VIMER v1.
  - serving topology: gunicorn behind Nginx as reverse proxy with TLS
  - intended for the production posture beyond the pilot

`DEPLOYMENT_PROFILE` fija valores predeterminados y exige los controles de
seguridad de producción. `DATABASE_URL` selecciona SQLite o PostgreSQL sin
desactivar HTTPS, cookies seguras, HSTS, CSP ni adjuntos privados. El servicio
`db` del compose de producción es opcional (`COMPOSE_PROFILES=postgresql`).

`runserver` is not a release deployment mode. It remains available for local development only.

## Consequences

Positive:

- one codebase, one container image, two profiles; no maintenance fork between pilot and production
- moving from pilot to production is a configuration change, not a re-engineering
- the existing `django-environ` pattern is preserved and extended, not replaced

Negative:

- the configuration surface grows; an operator switching modes without a checklist can ship a partially configured deployment
- SQLite serializa escritores con `IMMEDIATE`; su capacidad requiere medición y no se equipara a PostgreSQL.
- two `docker-compose.*.yml` files (one per profile) must be kept in sync for things they share

## Follow-Up

- introduce `DEPLOYMENT_PROFILE` parsing in `config/settings.py` with explicit defaults per profile
- ship `docker-compose.pilot.yml` and `docker-compose.production.yml` with the matching topologies
- document the `pilot -> production` migration as an operational runbook in `docs/release_plan_v1.md`
- explicitly reject `runserver` as a release option in `docs/adr/0009-accepted-release-risks.md`
