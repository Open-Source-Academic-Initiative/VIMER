# ADR 0009: Accepted Release Risks — No Formal Backup, Manual Recovery, Runserver Retired

## Status

Accepted

## Context

Building a release-ready posture without overspending on the pilot requires explicit choices about which operational guarantees are worth the cost. Three risks are taken consciously and documented here so that nobody assumes they are gaps to be closed silently.

The risks are not equivalent. One is a deliberate retirement of an old habit (`runserver` in production); the other two are reductions in operational safety net during the pilot window.

## Decision

VIMER's first release accepts the following three risks explicitly:

### 1. No formal backup of pilot data

- the pilot mode runs on SQLite at the default path, on a single VPS
- no scheduled backup pipeline is shipped with the release
- snapshots provided by the VPS hosting provider, if any, are the only recovery path
- the operator may choose to add a manual `cron` + `rclone`-to-external-storage pipeline outside the release scope
- T&C disclose to participants that the pilot is a controlled-data-loss-tolerant environment and that they should retain their own copies of materials submitted

### 2. Manual account recovery

- a representative who loses access to the email associated with their account has no automated reset path
- the recovery procedure is: contact the support email, the `Administrador de plataforma` validates identity off-band, the admin resets the email or password through Django Admin
- the procedure is documented in the FAQ and in the Política de Tratamiento under the ARCO+ rights section
- no in-product self-service identity-recovery flow ships in this release

### 3. `runserver` retired even in pilot mode

- ADR 0004 already commits gunicorn for both deployment profiles
- this ADR closes the door explicitly: the pilot mode does not fall back to `runserver` under any circumstance
- `runserver` remains acceptable for local development only

## Consequences

Positive:

- the operational surface of the release is small, predictable and shippable on a single VPS
- the costs and trade-offs are visible to participants instead of being hidden assumptions
- moving from pilot to production-grade backups and recovery becomes an explicit follow-up project rather than an emergency

Negative:

- a hardware or filesystem incident during the pilot window can lose the entire pilot dataset
- a representative locked out of email creates manual work for the operator, with no SLA
- the operator must hold the discipline of not using `runserver` for "just one demo"

## Follow-Up

- include a paragraph in T&C explaining the data-loss-tolerant nature of the pilot
- document the manual identity-recovery procedure in the FAQ and in `docs/release_plan_v1.md`
- when the volume or sensitivity of pilot data justifies it, schedule a follow-up release that closes risks 1 and 2 (production-grade backup pipeline, in-product password reset and email change with verification)
- the operator must declare the moment at which any of these risks stops being acceptable; the move to `DEPLOYMENT_PROFILE=production` is the natural trigger for risks 1 and 2
