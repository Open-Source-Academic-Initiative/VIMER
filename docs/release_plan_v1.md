# VIMER Release Plan v1 — Pilot Launch

## Status

Active.

This document is the rector plan for the first official release of VIMER. It consolidates the scope, the decisions, the work to do and the risks accepted to take the project from "working MVP with explicit domain architecture" to "controlled pilot in operation".

Subordinate to this document, but normative for the topics they own:

- `docs/adr/0004-dual-mode-deployment.md`
- `docs/adr/0005-multi-representative-onboarding.md`
- `docs/adr/0006-attachments-and-markdown-content.md`
- `docs/adr/0007-closed-challenge-taxonomy.md`
- `docs/adr/0008-pilot-launch-posture.md`
- `docs/adr/0009-accepted-release-risks.md`

If this document drifts from any of those ADRs, the ADRs win and this rector must be updated.

## 1. Purpose and Positioning

VIMER's first release is a closed pilot that operates the full marketplace cycle (`Desafío -> Propuesta -> Evaluación -> Adjudicación`) for a curated set of organizations under controlled conditions, while exercising the production-grade public flow.

What v1 is:

- a release that closes the open ends of the current MVP
- a controlled launch that validates the product end to end with real participants
- a configuration-only path to a production posture once the pilot proves the flow

What v1 is not:

- a public general availability launch
- a multi-jurisdiction or multi-currency product
- a billing or contract-management product
- an evaluation governance refinement (reapertura, apelación, recusación remain `Planned`)

Reference fotografía: this plan is anchored against the repository state described in `README.md`, `docs/domain/ontology_v4.md`, `docs/domain/invariants.md` and the codebase under `apps/` at the moment of the planning session.

## 2. Definition of Release

The first release is declared shipped when, and only when, the following functional criterion is satisfied, together with its prerequisites.

### 2.1 Functional criterion

All of the new flows below are implemented, covered by service-level and flow-level tests, and the full suite passes through `make verify-fast`:

- multi-representative onboarding with delegable titularity (ADR 0005)
- attachments and sanitized markdown on `Desafío` and `Propuesta` (ADR 0006)
- closed taxonomy of categorías and search/filter on the marketplace listing (ADR 0007)
- minimal `Administración de plataforma` dashboard with pilot KPIs
- T&C and Política de Tratamiento de Datos accepted at signup
- Cloudflare Turnstile active on signup
- email transactional path operational for password reset, email verification and duplicate of critical notifications
- public FAQ page published

### 2.2 Prerequisites that make the criterion possible

The following are not separate done criteria; they are enabling work without which the functional criterion cannot be true.

- operational: VPS+Docker dual-mode topology defined in ADR 0004 is reproducible from the repository, both profiles boot end to end, deploy procedure documented, smoke test executable
- documental and legal: T&C, Política de Tratamiento de Datos and FAQ are drafted (Spanish), reviewed by the operator, and published as static template pages
- governance: this rector is committed; ADRs 0004–0009 are committed; `docs/domain/ontology_v4.md`, `docs/domain/glossary.md`, `docs/domain/invariants.md` and `docs/domain/context_map.md` are updated to reflect the new concepts and invariants

A release that satisfies 2.1 without 2.2 is not a release; it is a code-complete state without launch capability.

## 3. Consolidated Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | Release type | Closed pilot, public-grade signup, URL distributed externally to participants only |
| 2 | Jurisdiction | Colombia only, Habeas Data minimum legal at signup (ADR 0008) |
| 3 | Monetization | Free of charge in this release |
| 4 | Deployment | VPS+Docker dual-mode: `pilot` (gunicorn+SQLite), `production` (Nginx+gunicorn+Postgres/MariaDB) (ADR 0004) |
| 5 | Persistence | Database engine agnostic via `DATABASE_URL`, no official engine matrix |
| 6 | Email | Gmail SMTP of the operator, ~500 sends/day ceiling assumed |
| 7 | Multi-representative | Self-association by tax identifier with titular approval; delegable titularity (ADR 0005) |
| 8 | Organization verification | Email of representative only |
| 9 | Anti-spam at signup | Cloudflare Turnstile |
| 10 | Account recovery | Manual reset by `Administrador de plataforma` (ADR 0009) |
| 11 | Support | Single email + FAQ |
| 12 | Observability | VPS logs + external uptime monitor |
| 13 | Configuration | `DEPLOYMENT_PROFILE` + granular env overrides |
| 14 | Content | Attachments (PDF/JPG/PNG) + sanitized markdown on both sides (ADR 0006) |
| 15 | Discovery | Search + filters + closed taxonomy of categorías (ADR 0007) |
| 16 | Post-adjudication | Pure matchmaking; product cycle closes at `AWARDED` |
| 17 | Advanced evaluation governance | Postponed |
| 18 | UI | Bootstrap 5 |
| 19 | Accessibility / mobile | Responsive minimum, no formal WCAG commitment |
| 20 | Admin reports | Django Admin + minimal KPI dashboard |
| 21 | Pilot backup | None formal; risk accepted (ADR 0009) |
| 22 | Pilot to production switch | Manual operator decision |
| 23 | Rector document | This file (`docs/release_plan_v1.md`) plus ADRs 0004–0009 |
| 24 | Release done | Functional criterion in section 2.1 with prerequisites in section 2.2 |

## 4. New Domain Scope

The following concepts are introduced or expanded in v1. Each is owned by a specific bounded context.

### 4.1 Identity and Corporate

- `Representante titular`: the holder of governance over an organization on the platform. The first registered representative is automatically the titular. Modeled as a flag on `User` enforced by a database constraint.
- `Solicitud de unión a organización`: persisted aggregate that represents a self-registered representative awaiting approval from the titular of an existing organization. Lifecycle: `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`.
- `Transferencia de titularidad`: an explicit action that moves titularity from one active representative to another within the same organization. Auditable through a domain event.
- `Aceptación de documentos legales`: persisted record that links a `User` to the version of T&C and Política de Tratamiento accepted at signup.

### 4.2 Marketplace

- `Categoría de desafío`: aggregate owned by `Administración de plataforma`. A `Desafío` references one or more categorías.
- `ChallengeAttachment` and `ApplicationAttachment`: persisted attachments with MIME-allowlisted content type, size cap and ownership FK. Filenames are normalized; URLs use opaque identifiers.
- Markdown-rendered long-form content on `Desafío.description` and on the four mandatory `Propuesta` components, sanitized server-side.

### 4.3 Notifications

- new event consumers for `RepresentativeJoinRequested`, `RepresentativeJoinApproved`, `RepresentativeJoinRejected`, `RepresentativeJoinExpired`, `OrganizationOwnershipTransferred`
- email-channel projection for password reset, email verification, and the existing critical evaluation notifications already produced by `apps/evaluation/`

### 4.4 New invariants

The numbering continues from the existing inventory in `docs/domain/invariants.md` (which currently goes up to `INV-34`, with `INV-40` and `INV-41` reserved for proposal lifecycle).

| Range | Topic | Owning ADR |
|---|---|---|
| `INV-50` to `INV-55` | Multi-representative and titularity | 0005 |
| `INV-56` to `INV-59` | Attachments and markdown | 0006 |
| `INV-60`, `INV-61` | Categorización | 0007 |
| `INV-62`, `INV-63` | Document acceptance at signup | 0008 |

The full text of each new invariant is authored in `docs/domain/invariants.md` as part of the release work.

## 5. New Functional Scope

### 5.1 Multi-representative onboarding

- signup form clears organization auto-association by tax identifier; if the organization exists, the new representative enters `PENDING_APPROVAL` and a `OrganizationJoinRequest` is created
- titular receives an internal notification and an email when a request arrives
- titular has a dedicated view to approve or reject pending requests for its organization
- titular has a dedicated action to transfer titularity to another active representative
- expiration of pending requests runs through a Django management command schedulable via cron

### 5.2 Content enrichment

- challenge publication form accepts up to N (default 5) attachments and renders markdown in `description`
- proposal save and submit flows accept up to N attachments per proposal and render markdown in the four structured components
- attachment download views enforce ownership and blind-evaluation rules
- markdown is rendered server-side with `markdown` and sanitized with `bleach`

### 5.3 Discovery

- challenge listing view exposes a search box (`q` parameter, ORM `icontains` over title and description), a category filter (`category` query param) and a status filter
- new `Categoría` admin in Django Admin
- seed migration with the initial agreed catalog of categorías

### 5.4 Identity hardening for public signup

- Cloudflare Turnstile widget on signup form
- mandatory acceptance of T&C and Política de Tratamiento at signup, persisted with version
- email verification flow for new representatives (token by email, no confirmation = no operation)
- password reset flow using Django's built-in views with email templates
- email duplication of critical notifications (`ChallengeAwarded`, `ApplicationEvaluationRecorded`, join-request lifecycle)

### 5.5 Platform administration dashboard

- new view `/admin/dashboard/` with simple table-based KPIs:
  - registered organizations and active representatives
  - challenges by lifecycle state
  - proposals submitted
  - mean time from `PUBLISHED` to `AWARDED`
  - registered evaluations in the last N days
- accessible only to platform administrators

### 5.6 Public-facing static pages

- T&C page (`/legal/terminos/`)
- Política de Tratamiento page (`/legal/politica-de-datos/`)
- FAQ page (`/ayuda/preguntas-frecuentes/`)
- Footer with support email and links to all three

## 6. New Operational Scope

### 6.1 Configuration profile

`config/settings.py` reads `DEPLOYMENT_PROFILE` (`pilot` or `production`) and applies coherent defaults:

- `pilot`: SQLite default, gunicorn binding `0.0.0.0:8000`, no HTTPS redirect by default, HSTS off by default, secure cookies off by default
- `production`: requires `DATABASE_URL`, `SECURE_SSL_REDIRECT=True`, HSTS on with subdomains and preload, secure cookies on, expects to live behind Nginx

Every default remains overridable through its own env var. The profile is a shortcut, not a policy.

### 6.2 Docker topology

Two compose files ship with the release:

- `docker-compose.pilot.yml`: single `web` service, gunicorn+SQLite, volume for `db.sqlite3` and `media/`
- `docker-compose.production.yml`: services for `web` (gunicorn), `db` (Postgres), `nginx` (reverse proxy with TLS via Certbot or external)

The `Dockerfile` remains single. The selection happens through the compose file used.

### 6.3 Deploy procedure

A short runbook section in this document covers:

1. clone the repository on the target VPS
2. set `.env` with `DEPLOYMENT_PROFILE`, `SECRET_KEY`, `ALLOWED_HOSTS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, `DATABASE_URL` if `production`
3. `docker compose -f docker-compose.<profile>.yml up -d --build`
4. `docker compose exec web python manage.py migrate`
5. `docker compose exec web python manage.py seed_categories` (one-shot for pilot)
6. `docker compose exec web python manage.py createsuperuser`
7. smoke test: open landing, signup with a throwaway email, confirm verification email arrives, log in

### 6.4 Logging and uptime

- Python logging configuration emits to stdout; the VPS captures container logs through the journald or docker logging driver
- one external uptime monitor (UptimeRobot or equivalent) pings the public landing URL on a schedule and emails on failure

### 6.5 No formal backup

Risk accepted (ADR 0009). Operator may add a manual backup pipeline outside the release scope.

## 7. New Documental and Legal Scope

The following are not engineering deliverables but are gating prerequisites for the release. They are listed here so that ownership is explicit.

| Artifact | Owner | Output |
|---|---|---|
| Términos y Condiciones VIMER v1 | operator + legal review | static template page in Spanish, version identifier `v1` |
| Política de Tratamiento de Datos Personales v1 | operator + legal review | static template page in Spanish, version identifier `v1`, identification of `Responsable del Tratamiento` and ARCO+ contact |
| Aviso de Privacidad | operator + legal review | short version visible at signup linking to the full Política |
| FAQ inicial | operator | 10–20 questions covering signup, organization roles, challenge publication, proposal submission, evaluation and support |
| Catálogo inicial de categorías | operator + product | seed list, agreed with pilot stakeholders, loaded by data migration |

## 8. Iteration Plan

The work is organized into seven slices, ordered by dependency. Each slice is closed when its code lands, its tests pass and the related documents are updated.

### Slice 1 — Domain foundations

Goal: introduce the new aggregates and invariants in code, migrations and admin.

Scope:

- model `OrganizationJoinRequest`, titular flag on `User`, `Categoría`, `ChallengeAttachment`, `ApplicationAttachment`, document acceptance record
- migrations for all new models with appropriate constraints
- skeleton domain rule modules for the new invariants
- minimal Django Admin registrations for new models

Closure: schema migrations apply cleanly on a fresh DB, `python manage.py check` passes, model tests cover the new constraints.

### Slice 2 — Application services and write flows

Goal: orchestrate the new write-side use cases through application services.

Scope:

- `RegisterRepresentative` service updated to handle auto-association and pending state
- `ApproveJoinRequest`, `RejectJoinRequest`, `TransferOrganizationOwnership` services
- challenge publication and edit services accept categorías and attachments
- proposal save/submit services accept attachments and markdown in long-form fields
- markdown sanitization service centralized
- domain events emitted for the new identity flows; new consumers in `apps/notifications/`

Closure: service-level tests cover the happy path and the negative paths for each new service. Email content templates are added.

### Slice 3 — Read views, templates and discovery

Goal: bring the new flows to the user-facing surface.

Scope:

- views and templates for the multi-representative flows (request listing, approve, reject, transfer titularity)
- challenge form and template updated with categorías, markdown editor and attachments upload/download
- proposal form and template updated with attachments and markdown
- marketplace listing with search box, category filter, status filter
- attachment download views with permission checks
- Bootstrap 5 integration across templates

Closure: flow-level tests cover at least one happy path per new view. Visual smoke test on a local browser session against the pilot profile.

### Slice 4 — Identity hardening for public signup

Goal: make the public signup safe enough for an exposed URL.

Scope:

- Cloudflare Turnstile integration in signup form, with verification in the registration service
- Django's `PasswordResetView` family enabled and customized with branded email templates
- email verification flow on signup with a token model, verification view and email template
- account state preventing operation until email is verified
- footer with support email
- T&C and Política de Tratamiento checkbox on signup, with version capture

Closure: registration cannot succeed without Turnstile, without email verification (subsequent operations), or without checked T&C/Política. Password reset lifecycle is covered by tests.

### Slice 5 — Legal and content artifacts

Goal: publish the legal and helpful content gating the release.

Scope:

- static template pages for T&C, Política de Tratamiento and FAQ
- routes and footer links
- copy review by operator
- legal review of T&C and Política
- catálogo inicial loaded by data migration

Closure: pages are reachable, content is approved, links work.

### Slice 6 — Operational

Goal: make the release reproducibly deployable.

Scope:

- `DEPLOYMENT_PROFILE` parsing in settings
- `docker-compose.pilot.yml` and `docker-compose.production.yml`
- Nginx config and TLS for production profile
- logging configuration to stdout
- platform administration dashboard
- smoke test script
- deploy runbook section in this document

Closure: a dry-run deploy of both profiles succeeds end to end on a clean machine.

### Slice 7 — Governance and traceability

Goal: leave the release with a coherent, versioned domain corpus.

Scope:

- update `docs/domain/ontology_v4.md` with new concepts and events
- update `docs/domain/glossary.md` with new canonical terms
- update `docs/domain/invariants.md` with `INV-50` through `INV-63`
- update `docs/domain/context_map.md` with `Identity` extension and the `Notifications -> email` channel
- update `docs/ddd_work_plan.md` with the v1 iteration as a closed phase and the next phase as the post-pilot move
- update `README.md` with a release v1 section and link to this rector

Closure: all referenced files exist, the `make verify-fast` validation still passes, the rector document remains authoritative.

## 9. Accepted Risks and Postponed Work

### 9.1 Accepted risks (ADR 0009)

- no formal backup of pilot data
- manual identity recovery only
- email transaction limited by Gmail SMTP send-rate ceiling

### 9.2 Postponed work, explicitly out of v1

- billing, payments, plans, electronic invoicing
- multi-jurisdiction or RGPD compliance
- KYC, organization verification beyond email of representative
- advanced evaluation governance: reapertura, apelación, recusación de evaluador
- formal WCAG commitment beyond responsive layout
- ticket-based support inside the application
- in-product mensajería between Solicitante and Proveedor after `AWARDED`
- object storage for attachments
- Sentry, APM or business analytics beyond the minimal admin dashboard
- user-defined tags on challenges (taxonomy stays closed in v1)

### 9.3 Operational triggers for closing risks later

- the move to `DEPLOYMENT_PROFILE=production` is the natural moment to close risks 1 and 2 from ADR 0009
- when daily email volume approaches the Gmail SMTP ceiling, the operator must migrate to a transactional provider (Resend, Postmark, SES)
- when pilot adjudications become contractually relevant, advanced evaluation governance must be revisited

## 10. Cross-References

| Concern | Authoritative source |
|---|---|
| Ontology and concepts | `docs/domain/ontology_v4.md` |
| Canonical terms | `docs/domain/glossary.md` |
| Bounded contexts and integration | `docs/domain/context_map.md` |
| Invariant inventory | `docs/domain/invariants.md` |
| Approved scoring policy | `docs/domain/evaluation_scoring_and_award_policy.md` |
| DDD work plan | `docs/ddd_work_plan.md` |
| Functional and architecture diagrams | `docs/project_diagrams.md` |
| Test strategy and benchmarks | `docs/testing_strategy.md` |
| Deployment dual-mode | `docs/adr/0004-dual-mode-deployment.md` |
| Multi-representative onboarding | `docs/adr/0005-multi-representative-onboarding.md` |
| Attachments and markdown | `docs/adr/0006-attachments-and-markdown-content.md` |
| Closed taxonomy | `docs/adr/0007-closed-challenge-taxonomy.md` |
| Pilot launch posture | `docs/adr/0008-pilot-launch-posture.md` |
| Accepted release risks | `docs/adr/0009-accepted-release-risks.md` |
