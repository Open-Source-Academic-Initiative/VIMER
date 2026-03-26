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
apps/evaluation/
apps/notifications/
docs/
templates/
```

Current validated baseline:

- MVP flow is working end to end.
- `identity` already uses an application service for registration.
- `marketplace` already uses application services for challenge publication and application submission.
- `evaluation` already exists as an explicit bounded module/app for team governance, scoring, adjudication, timeline, and blind evaluation flows.
- `notifications` already exists as an explicit bounded module/app fed by evaluation events.
- Versioned domain references already exist under `docs/domain/`.
- Core role rules already exist in web, service, model, and database layers.
- Challenge lifecycle, structured proposal components, explicit evaluation criteria, and multiple evaluators per criterion are already implemented.
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

Status:

- `Implemented`

Actions:

- Create `docs/domain/` for versioned domain references.
- Add a single canonical ontology document that absorbs the evolving local ontological model.
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

- `docs/domain/ontology_v4.md`
- `docs/domain/glossary.md`
- `docs/domain/context_map.md`
- `docs/domain/invariants.md`
- `docs/adr/` initial ADR set

Exit criteria:

- Core domain concepts are documented in Git.
- The ontology is no longer split across local notes and versioned fragments.
- New feature work can reference versioned artifacts instead of local notes.

### 2. Explicit domain enforcement for the current MVP

Objective:

- Convert the current MVP rules into named, traceable domain rules.

Status:

- `Implemented` in `marketplace`
- `Implemented` in `evaluation`

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

Status:

- `Implemented internally`, `Partial physically`

Actions:

- Keep the physical Django app while preserving separated internal ownership:
  - challenge-oriented concerns
  - application-oriented concerns
- Keep commands, services, forms, views, and tests assigned to one subdomain by default.
- Add new marketplace behavior only through the subdomain slice that owns it.

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
- Status note:
  - the internal split is already in place through separated domain/application modules plus challenge/application forms, views, and test classes

### 4. Evolve `Challenge` into a real aggregate

Objective:

- Move from a minimal publication record to a challenge aggregate with lifecycle.

Status:

- `Implemented` for lifecycle, deadlines, and evaluation criteria foundation

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

Status:

- `Implemented` for structured submission and immutability
- `Partial` for draft lifecycle

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

### 6. Deepen the `Evaluation` context

Objective:

- Continue evolving the already-open evaluation context toward richer decision governance.

Status:

- `Implemented` for the core cycle
- `Implemented` for equal-weight scoring and tie-aware adjudication
- `Next` for deeper audit and governance refinements

Minimum domain additions:

- richer audit and event consumers
- deeper governance of evaluation decisions

Actions:

- Preserve `apps/evaluation/` as the explicit evaluation context.
- Revisit criterion weighting only if product semantics later require non-uniform scoring.
- Deepen audit read models and event consumers around evaluation activity.
- Revisit whether adjudication needs additional governance controls beyond the current designated-role model.

Suggested first scope:

- keep one winning proposal at most per challenge
- preserve mandatory rationale
- preserve blind evaluation until award
- enrich audit and scoring semantics without collapsing concerns back into `marketplace`

Exit criteria:

- The current evaluation context reflects the next layer of domain semantics without reintroducing implicit behavior.

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
- Optimize heavy suites with shared immutable fixtures and a documented fast execution path.
- Expand negative test coverage for permissions, state transitions, and validation failures.
- Add deployment-oriented documentation and a real production serving strategy.
- Revisit `manage.py check --deploy` findings under a proper non-debug environment.

Exit criteria:

- Domain evolution does not increase operational fragility.
- Validation remains fast enough to run continuously during local iteration.

## Recommended Execution Order

1. Keep versioned domain artifacts synchronized
2. Deepen `Evaluation` with richer audit and governance
3. Preserve the internal split discipline of `marketplace`
4. Decide whether `Application` needs a persisted draft lifecycle
5. Continue semantic convergence
6. Harden operations alongside domain work

## Iteration Plan

### Completed foundation

- domain governance and traceability
- explicit invariant enforcement for the current MVP
- challenge lifecycle
- structured proposal formalization
- evaluation and adjudication context

### Current iteration focus

- keep `README.md`, `docs/domain/*`, and local tracking notes synchronized
- preserve multi-evaluator blind evaluation semantics already implemented
- enrich evaluation audit and event consumers without broadening `marketplace`

### Next iteration focus

- richer audit consumers and decision governance in `evaluation`
- preserve the current internal split of `marketplace` and keep new behavior inside the right ownership slice
- decision on persisted draft lifecycle for `Application`

## Definition of Done per Domain Feature

Every domain-aligned feature should include:

1. versioned specification
2. invariant list
3. application service or domain rule implementation
4. persistence enforcement where applicable
5. web-flow coverage
6. service-level coverage
7. documentation update

## Immediate Next Slice Proposal

The next slice should focus on the minimum work that increases domain fidelity without reopening already-closed slices.

Scope:

- deepen event consumers and audit projections around evaluation activity
- add more traceable invariant-to-test coverage
- keep challenge-facing and application-facing concerns separated inside `apps/marketplace/`

Recommended file targets for the next slice:

- `apps/evaluation/domain/handlers.py`
- `apps/notifications/domain/handlers.py`
- `apps/evaluation/models.py`
- `apps/evaluation/tests.py`
- `docs/domain/ontology_v4.md`
- `docs/domain/invariants.md`

## Risks to Manage

- introducing DDD language only in documentation and not in code
- renaming too early and destabilizing the MVP
- mixing evaluation concerns back into `marketplace`
- adding states without clearly enforced transitions
- allowing local ignored notes to diverge again from versioned project knowledge

## Final Recommendation

The safest and highest-leverage path now is:

- keep the versioned domain corpus authoritative
- deepen `Evaluation` before widening the surface area
- preserve the current conceptual split of `marketplace` without a risky physical rewrite
- rename technical legacy concepts only when the model is already stable

This keeps the current baseline useful while moving VIMER from "working MVP with explicit domain architecture" toward "working MVP with tighter semantic, tactical, and operational discipline".
