# VIMER Context Map

## Purpose

This document defines the current and target bounded-context view of VIMER.

The current codebase is still organized mostly around:

- `identity`
- `corporate`
- `marketplace`
- `evaluation`

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
- proposal submission
- challenge browsing

Current code:

- `apps/marketplace/`

Issue:

- `Marketplace` is currently broader than the domain suggests.

### Evaluation

Responsibilities today:

- transition from published challenge to evaluation
- adjudication decision
- winning proposal selection with mandatory comment

Current code:

- `apps/evaluation/`

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
- proposal lifecycle
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
- adjudication decision
- evaluation outcomes

Consumes from:

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
- Split internals by domain concern:
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

### Platform Administration

- Operates across contexts but should not distort the core market language.

## Refactor Priority

1. Split `marketplace` conceptually into `Challenge` and `Application`.
2. Add lifecycle semantics to `Challenge`.
3. Add structured proposal semantics to `Application`.
4. Introduce `Evaluation`.
5. Revisit technical names later, once behavior stabilizes.
