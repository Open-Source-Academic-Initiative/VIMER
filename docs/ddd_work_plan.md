# DDD / Ontology Work Plan for VIMER

## Purpose

This document turns the DDD and ontological direction described in the local analysis notes into an executable work plan for the current codebase.

The goal is not to rebuild VIMER from scratch. The goal is to evolve the current baseline in controlled iterations so the software reflects the domain model with increasing fidelity.

## Current Baseline

The plan assumes the current repository structure:

```text
config/
apps/identity/
apps/corporate/
apps/marketplace/
templates/
```

Current validated baseline:

- MVP flow is working end to end.
- `identity` already uses an application service for registration.
- `marketplace` already uses application services for challenge publication and application submission.
- Core role rules already exist in web, service, model, and database layers.
- The project is still development-oriented and is not production-ready yet.

## Planning Principles

1. Preserve the current working MVP while evolving the model.
2. Prefer incremental extraction over large rewrites.
3. Introduce domain rules explicitly before doing semantic renames.
4. Every important invariant must end up in code and tests.
5. Keep a clear distinction between:
   - web layer
   - application layer
   - domain rules
   - persistence
6. Avoid growing `apps/marketplace` as an unbounded catch-all module.

## Target Domain Direction

The target conceptual split is:

- `Identity`: human actors, authentication, representation.
- `Corporate`: organizations, market role, organization profile.
- `Challenge`: challenge lifecycle and publication rules.
- `Application`: proposal lifecycle and submission rules.
- `Evaluation`: adjudication and evaluation decisions.
- `Platform Administration`: technical governance and operational control.

For now, `Challenge`, `Application`, and `Evaluation` can evolve inside the current repository without forcing an immediate app-level rename.

## Workstreams

### 1. Governance and versioned domain knowledge

Objective:

- Move the key domain decisions from ignored local notes into versioned project artifacts.

Actions:

- Create `docs/domain/` for versioned domain references.
- Add ADRs for:
  - bounded context strategy
  - naming strategy between business terms and technical legacy names
  - invariant enforcement strategy
- Add a lightweight template for feature specs:
  - business goal
  - invariant list
  - state transitions
  - test plan

Deliverables:

- `docs/domain/glossary.md`
- `docs/domain/context_map.md`
- `docs/domain/invariants.md`
- `docs/adr/` initial ADR set

Exit criteria:

- Core domain concepts are documented in Git.
- New feature work can reference versioned artifacts instead of local notes.

### 2. Explicit domain enforcement for the current MVP

Objective:

- Convert the current MVP rules into named, traceable domain rules.

Current rules already present in the codebase:

- only demand-side organizations can publish challenges
- only supply-side organizations can apply to challenges
- a provider cannot apply twice to the same challenge
- a superuser cannot delete itself from Django Admin

Actions:

- Introduce explicit domain rule modules inside `apps/marketplace/` and, where useful, `apps/identity/`.
- Move role enforcement and duplicate-application logic toward named rule objects or domain services.
- Keep model validation and database constraints as final safety nets.
- Add traceability from each rule to tests.

Suggested structure:

```text
apps/marketplace/
  application/
  domain/
    rules.py
    services.py
    invariants.py
```

Exit criteria:

- The main business rules are no longer implicit only in views or models.
- Each important rule has at least one service-level test and one flow-level test.

### 3. Conceptual split of `marketplace`

Objective:

- Stop treating `marketplace` as a single vague bounded context.

Actions:

- Split the internals of `apps/marketplace/` into two clear slices:
  - challenge-oriented concerns
  - application-oriented concerns
- Keep the physical Django app if needed, but separate modules and ownership.
- Separate commands, services, forms, and tests by subdomain.

Suggested internal direction:

```text
apps/marketplace/
  challenge/
  application_submission/
  application/
```

If that structure feels too disruptive, use:

```text
apps/marketplace/
  domain/challenges.py
  domain/applications.py
  application/challenges.py
  application/applications.py
```

Exit criteria:

- Publication and submission logic no longer live in a single generic bucket.
- Teams can evolve challenge and proposal behavior independently.

### 4. Evolve `Challenge` into a real aggregate

Objective:

- Move from a minimal publication record to a challenge aggregate with lifecycle.

Minimum domain additions:

- `status`
- `application_deadline`
- evaluation criteria foundation

Proposed first status model:

- `DRAFT`
- `PUBLISHED`
- `CLOSED`
- `UNDER_EVALUATION`
- `AWARDED`
- `ARCHIVED`

Actions:

- Add status and deadline fields to the challenge model.
- Define valid state transitions.
- Forbid applications when the challenge is not open for submission.
- Add application deadline enforcement.
- Reflect status in forms, service rules, and templates.

Exit criteria:

- A challenge has lifecycle semantics, not just content fields.
- State transition rules are enforced in code and covered by tests.

### 5. Evolve `Application` into a real proposal aggregate

Objective:

- Move from a free-text submission to a domain proposal with structure and lifecycle.

Minimum domain additions:

- proposal structure with required components
- optional draft state before final submission
- post-submission immutability policy

Suggested mandatory components:

- problem understanding
- proposed solution
- capabilities / evidence
- execution approach or implementation plan

Actions:

- Replace or extend `proposal_text` with a structured proposal model.
- Decide whether drafts are needed in this phase or the next one.
- Define what can change before and after submission.
- Add validation rules for completeness.

Exit criteria:

- A proposal is a domain object with explicit semantics.
- Submission invariants are represented as code, not only as form behavior.

### 6. Open the `Evaluation` context

Objective:

- Implement the missing part of the core cycle: evaluation and adjudication.

Minimum domain additions:

- `DecisionDeAdjudicacion`
- mandatory adjudication comment
- assignment of evaluation responsibility

Actions:

- Create a new Django app or a new bounded module for evaluation.
- Model the adjudication decision independently of challenge publication and proposal submission.
- Define read and write flows for evaluation.
- Prepare event emission points for major lifecycle changes.

Suggested first scope:

- one winning proposal at most per challenge
- mandatory rationale
- explicit status updates after adjudication

Exit criteria:

- The central domain cycle becomes executable:
  `Challenge -> Application -> Evaluation / Adjudication`

### 7. Semantic convergence

Objective:

- Reduce the gap between ubiquitous language and code without destabilizing the baseline.

Actions:

- Keep business-facing language canonical in templates, docs, and tests.
- Delay model renames until after lifecycle and invariant work is stable.
- Evaluate later whether `Challenge` and `Application` should remain as technical names or be migrated.

Recommended order:

1. canonical business language in docs
2. canonical business language in templates and labels
3. canonical business language in test naming
4. optional technical rename in code when the model stabilizes

Exit criteria:

- The semantic debt is controlled and intentional.
- The codebase is easier to reason about across domain, UI, and tests.

### 8. Operational hardening alongside domain work

Objective:

- Prevent architectural progress from being undermined by fragile operational behavior.

Actions:

- Isolate test configuration from local `.env` side effects.
- Expand negative test coverage for permissions, state transitions, and validation failures.
- Add deployment-oriented documentation and a real production serving strategy.
- Revisit `manage.py check --deploy` findings under a proper non-debug environment.

Exit criteria:

- Domain evolution does not increase operational fragility.

## Recommended Execution Order

1. Governance and versioned domain knowledge
2. Explicit domain enforcement for the current MVP
3. Conceptual split of `marketplace`
4. Evolve `Challenge` into a real aggregate
5. Evolve `Application` into a real proposal aggregate
6. Open the `Evaluation` context
7. Semantic convergence
8. Operational hardening alongside domain work

## Iteration Plan

### Iteration A: domain governance and traceability

Goal:

- Make the discovered domain versioned and operational.

Deliverables:

- `docs/domain/` base set
- initial ADRs
- invariant inventory
- feature-spec template

Success signal:

- The team can point to one versioned source of truth for domain decisions.

### Iteration B: enforce current invariants explicitly

Goal:

- Turn existing business rules into named domain behavior.

Deliverables:

- domain rules inside `apps/marketplace/`
- traceability from invariants to tests
- missing negative tests for current rules

Success signal:

- The current MVP rules are visible, named, and testable as domain behavior.

### Iteration C: challenge lifecycle

Goal:

- Add lifecycle semantics to `Challenge`.

Deliverables:

- challenge status
- application deadline
- state transition rules
- tests for open/closed behavior

Success signal:

- Applications only happen in valid challenge states.

### Iteration D: proposal formalization

Goal:

- Turn `Application` into a structured proposal aggregate.

Deliverables:

- required proposal components
- completeness validation
- immutability or controlled edit policy
- tests for invalid and valid submissions

Success signal:

- Proposal submission has domain meaning beyond free-form text entry.

### Iteration E: evaluation and adjudication

Goal:

- Complete the core business cycle.

Deliverables:

- evaluation module or app
- adjudication decision
- rationale/comment requirement
- post-adjudication transitions

Success signal:

- A challenge can progress through decision-making, not only publication and application.

### Iteration F: semantic and technical cleanup

Goal:

- Reduce naming and architectural debt once the domain shape stabilizes.

Deliverables:

- naming cleanup plan
- refactors with safety from tests
- docs synchronization pass

Success signal:

- The codebase language aligns more naturally with the domain.

## Definition of Done per Domain Feature

Every domain-aligned feature should include:

1. versioned specification
2. invariant list
3. application service or domain rule implementation
4. persistence enforcement where applicable
5. web-flow coverage
6. service-level coverage
7. documentation update

## First Sprint Proposal

The first sprint should focus on the minimum work that creates leverage for all later iterations.

Scope:

- create `docs/domain/`
- write `glossary.md`
- write `invariants.md`
- add 2 to 3 ADRs
- extract current marketplace rules to named domain modules
- add missing negative tests for:
  - invalid role publishing
  - invalid role application
  - duplicate application at service and flow level
  - challenge closure once statuses exist

Recommended file targets for the first sprint:

- `docs/domain/glossary.md`
- `docs/domain/invariants.md`
- `docs/adr/0001-bounded-context-strategy.md`
- `docs/adr/0002-naming-strategy.md`
- `apps/marketplace/domain/`
- `apps/marketplace/tests.py`

## Risks to Manage

- introducing DDD language only in documentation and not in code
- renaming too early and destabilizing the MVP
- mixing evaluation concerns back into `marketplace`
- adding states without clearly enforced transitions
- allowing local ignored notes to diverge again from versioned project knowledge

## Final Recommendation

The safest and highest-leverage path is:

- version the domain knowledge first
- formalize the existing invariants second
- add lifecycle semantics third
- introduce evaluation fourth
- rename technical legacy concepts only when the model is already stable

This keeps the current baseline useful while moving VIMER from "working MVP with implicit domain intuition" to "working MVP with explicit, enforceable domain architecture".
