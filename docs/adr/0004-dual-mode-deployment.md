# ADR 0004: Dual-Mode Deployment for Pilot and Production

## Status

Accepted

## Context

The first official release of VIMER is scoped as a closed pilot whose URL is distributed only to invited participants, but the same codebase must remain capable of a production-grade deployment posture later, without a rewrite or a divergent branch.

Two operational realities differ between pilot and production:

- the persistence engine
- the front-end serving topology

The application server itself is not a point of variation: gunicorn was already adopted in `Dockerfile` and `docker-compose.yml` to replace Django's development server, and that decision is preserved across both modes.

## Decision

VIMER will ship a single codebase that supports two deployment profiles through configuration only:

- `DEPLOYMENT_PROFILE=pilot`
  - persistence: SQLite at the default path
  - serving topology: gunicorn exposed directly behind whatever TLS terminator the operator chooses, or unencrypted when bound to a closed network
  - intended for the controlled pilot phase
- `DEPLOYMENT_PROFILE=production`
  - persistence: PostgreSQL or MariaDB through `DATABASE_URL`
  - serving topology: gunicorn behind Nginx as reverse proxy with TLS
  - intended for the production posture beyond the pilot

`DEPLOYMENT_PROFILE` only sets coherent defaults. Every subsystem remains overridable through its own environment variable (`DATABASE_URL`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `EMAIL_*`, `CSRF_TRUSTED_ORIGINS`, `ALLOWED_HOSTS`, `STORAGES`). The profile is a shortcut, not a lock.

`runserver` is not a release deployment mode. It remains available for local development only.

## Consequences

Positive:

- one codebase, one container image, two profiles; no maintenance fork between pilot and production
- moving from pilot to production is a configuration change, not a re-engineering
- the existing `django-environ` pattern is preserved and extended, not replaced

Negative:

- the configuration surface grows; an operator switching modes without a checklist can ship a partially configured deployment
- the SQLite-in-pilot choice limits concurrency and excludes migration tooling that depends on Postgres-only features
- two `docker-compose.*.yml` files (one per profile) must be kept in sync for things they share

## Follow-Up

- introduce `DEPLOYMENT_PROFILE` parsing in `config/settings.py` with explicit defaults per profile
- ship `docker-compose.pilot.yml` and `docker-compose.production.yml` with the matching topologies
- document the `pilot -> production` migration as an operational runbook in `docs/release_plan_v1.md`
- explicitly reject `runserver` as a release option in `docs/adr/0009-accepted-release-risks.md`
