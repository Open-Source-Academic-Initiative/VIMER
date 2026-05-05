# VIMER Context Map

## Purpose

This document defines the current and target bounded-context view of VIMER.

It complements `docs/domain/ontology_v4.md`, which is the canonical ontology.

The current codebase is still organized mostly around:

- `identity`
- `corporate`
- `marketplace`
- `evaluation`
- `notifications`

The target domain view is more explicit and should guide future refactors.

## Current Context View

### Identity

Responsibilities:

- authentication
- signup
- representative account lifecycle

Current code:

- `apps/identity/`

### Corporate

Responsibilities:

- organization data
- market role ownership
- organization profile and branding

Current code:

- `apps/corporate/`

### Marketplace

Responsibilities today:

- challenge publication
- challenge evaluation criteria definition
- structured challenge evaluation criteria
- proposal submission
- challenge browsing

Current code:

- `apps/marketplace/`

Issue:

- `Marketplace` is currently broader than the domain suggests.

### Evaluation

Responsibilities today:

- transition from published challenge to evaluation
- evaluation-team governance with designated evaluators, one designated adjudicator, and optional observers
- criterion-by-criterion proposal assessment by one or more designated evaluators
- proposal evaluation summaries for comparison and adjudication
- comparative proposal ranking
- tie-aware adjudication support and traceability
- adjudication decision
- winning proposal selection with mandatory comment
- award snapshot traceability
- persisted challenge evaluation timeline
- event-driven notifications for applicants and the evaluation team

Current code:

- `apps/evaluation/`

### Notifications

Responsibilities today:

- event-driven internal notifications
- unread notification tracking
- notification inbox for representatives

Current code:

- `apps/notifications/`

## Target Context View

### Identity

Owns:

- representatives
- authentication
- access entrypoints

Depends on:

- `Corporate` for organization association

### Corporate

Owns:

- organization
- market role
- organization profile

Supplies to:

- `Challenge`
- `Application`
- `Platform Administration`

### Challenge

Owns:

- challenge publication
- challenge lifecycle
- evaluation criteria foundation
- structured evaluation-criteria entries
- challenge state transitions
- application window

Consumes from:

- `Corporate`

Supplies to:

- `Application`
- `Evaluation`

### Application

Owns:

- proposal submission
- proposal lifecycle (`DRAFT -> SUBMITTED`)
- submission completeness rules
- duplicate submission prevention

Consumes from:

- `Challenge`
- `Corporate`

Supplies to:

- `Evaluation`

### Evaluation

Owns:

- proposal review
- evaluation-team governance
- criterion assessments
- proposal evaluation read models / summaries
- comparative ranking
- adjudication decision
- award-decision snapshot traceability
- challenge-facing evaluation timeline projection
- evaluation outcomes

Consumes from:

- `Challenge`
- `Application`

Supplies to:

- `Notifications`

### Notifications

Owns:

- internal user notifications
- unread/read state
- event-driven inbox entries

Consumes from:

- `Evaluation`
- `Challenge`
- `Application`

### Platform Administration

Owns:

- platform governance
- operational administration
- superuser-managed actions

Consumes from:

- `Identity`
- `Corporate`
- `Challenge`
- `Application`
- `Evaluation`

## Recommended Repository Direction

Short term:

- Keep `apps/marketplace/` as the physical Django app.
- Preserve the internal split by domain concern:
  - challenge-focused modules
  - application-focused modules

Medium term:

- Keep `Evaluation` isolated as its own Django app and prevent the logic from drifting back into `marketplace`.

Long term:

- Reassess whether physical app boundaries should match bounded contexts directly.

## Integration Notes

### Identity -> Corporate

- A representative belongs to an organization.

### Corporate -> Challenge

- Only a `Solicitante` organization can publish a challenge.

### Corporate -> Application

- Only a `Proveedor tecnológico` organization can submit a proposal.

### Challenge -> Application

- A proposal always targets one challenge.
- A challenge may receive many proposals.

### Challenge + Application -> Evaluation

- Evaluation operates on proposals in the context of a challenge.
- Publisher-facing evaluation read models should not leak outside the publisher organization boundary.

### Evaluation -> Challenge

- Evaluation persists challenge-facing timeline projections for major milestones.

### Evaluation -> Notifications

- Evaluation emits events that can be consumed for internal user notifications.

### Platform Administration

- Operates across contexts but should not distort the core market language.

## Refactor Priority

1. Preserve `marketplace` internal ownership boundaries between `Challenge` and `Application`.
2. Deepen `Notifications` and audit consumers around evaluation events.
3. Deepen evaluation governance and audit now that the approved equal-weight scoring and tie-aware adjudication policy is implemented.
4. Revisit technical names later, once behavior stabilizes.

## Release v1 Context Extensions

The first official release (`docs/release_plan_v1.md`) extends the responsibilities of three existing contexts and introduces no new bounded context. The bounded-context inventory of the platform stays the same.

### Identity (extended)

New responsibilities planned for v1:

- onboarding of additional representatives into an existing organization through self-association by tax identifier
- governance of `Solicitud de unión a organización` aggregates with explicit lifecycle (`PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`) and titular-only approval authority
- governance of titularity, including its transfer between active representatives of the same organization
- email verification of new representatives before they can operate
- recording of accepted versions of T&C and Política de Tratamiento at signup

New domain events emitted:

- `RepresentativeJoinRequested`
- `RepresentativeJoinApproved`
- `RepresentativeJoinRejected`
- `RepresentativeJoinExpired`
- `OrganizationOwnershipTransferred`
- `LegalDocumentsAccepted`

### Marketplace (extended)

New responsibilities planned for v1:

- closed taxonomy of `Categorías de desafío`, owned by `Administración de plataforma`
- challenge association to one or more categorías as a publication requirement
- search-by-text and filter-by-category exposed in the marketplace listing
- attachments on `Desafío` and on `Application`
- markdown rendering and sanitization of long-form content on both sides

### Notifications (extended)

New responsibilities planned for v1:

- consumption of identity events for in-app inbox entries (join request lifecycle, titularity transfer)
- email-channel projection of critical evaluation notifications and identity events through the operator's Gmail SMTP relay
- email-channel projection of password reset and email verification flows

### Integration additions

#### Identity -> Notifications

- identity emits join-request and titularity-transfer events; notifications consumes them for in-app inbox and email projection.

#### Identity -> Marketplace and Evaluation (preconditions)

- pending-approval and unverified-email accounts are blocked at the application-service boundary; this is enforced by `Identity` and respected by all downstream contexts.

#### Marketplace -> Administración de plataforma

- category catalog management is exposed exclusively through Django Admin; the marketplace context consumes the catalog read-only at challenge publication time.

### What v1 does not change

- the existing bounded-context boundaries are not redrawn
- `apps/marketplace/` remains a single physical Django app with its current internal split between `Challenge` and `Application` concerns
- `Evaluation` and the approved equal-weight scoring policy remain unchanged
- post-adjudication, VIMER stays a matchmaker; no new context is introduced for contract handoff
