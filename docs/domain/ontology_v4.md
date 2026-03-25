# VIMER Ontology v4

## Purpose

This document is the single canonical ontology for VIMER.

It supersedes earlier local v2/v3 ontological notes and should be treated as the authoritative domain reference for:

- business terms
- actors and roles
- bounded-context responsibilities
- core entities and read models
- permissions
- lifecycle states
- domain events and traceability
- implemented and planned domain rules

Companion documents remain useful, but subordinate:

- `docs/domain/glossary.md`
- `docs/domain/context_map.md`
- `docs/domain/invariants.md`

If any of those documents drift from this file, this file wins and the companions must be updated.

## Status Legend

- `Implemented`: present in the current codebase
- `Partial`: concept exists but is not enforced consistently yet
- `Planned`: desired target, not implemented yet

## Canonical Domain Layers

### Market Actors

#### Solicitante

- Type: organization business role
- Meaning: organization that publishes a `Desafío`
- Status: `Implemented`
- Technical mapping: `corporate.Organization.role == DEMAND_SIDE`

#### Proveedor tecnológico

- Type: organization business role
- Meaning: organization that submits a `Propuesta`
- Status: `Implemented`
- Technical mapping: `corporate.Organization.role == SUPPLY_SIDE`

#### Representante

- Type: human actor
- Meaning: authenticated user acting on behalf of an organization
- Status: `Implemented`
- Technical mapping: `identity.User`

### Evaluation Governance Roles

These are not market roles. They are operational roles inside the evaluation process of a published challenge.

#### Evaluador designado

- Meaning: representative explicitly authorized to score a proposal criterion by criterion
- Status: `Implemented`
- Technical mapping: `evaluation.ChallengeEvaluationRoleAssignment(role=EVALUATOR)`

#### Adjudicador designado

- Meaning: representative explicitly authorized to register the final award decision
- Status: `Implemented`
- Technical mapping: `evaluation.ChallengeEvaluationRoleAssignment(role=ADJUDICATOR)`

#### Observador de evaluacion

- Meaning: representative explicitly linked to the evaluation team for visibility/governance without mutation authority
- Status: `Implemented`
- Technical mapping: `evaluation.ChallengeEvaluationRoleAssignment(role=OBSERVER)`
- Note:
  - the same representative may hold more than one evaluation-governance role for the same challenge in the current model

### Platform Governance

#### Administracion de plataforma

- Meaning: cross-context technical governance and operational administration
- Status: `Implemented`
- Technical mapping: Django admin, superusers, deployment/runtime governance

## Bounded Contexts

### Identity

- Status: `Implemented`
- Owns:
  - representatives
  - authentication
  - account lifecycle
- Technical mapping:
  - `apps/identity/`

### Corporate

- Status: `Implemented`
- Owns:
  - organizations
  - market roles
  - organization profile and branding
- Technical mapping:
  - `apps/corporate/`

### Challenge

- Status: `Implemented conceptually`, `Partial physically`
- Owns:
  - challenge publication
  - challenge lifecycle
  - evaluation criteria foundation
  - structured evaluation criteria
  - application window
- Technical mapping today:
  - `apps/marketplace/models.py::Challenge`
  - `apps/marketplace/models.py::ChallengeEvaluationCriterion`

### Application

- Status: `Implemented conceptually`, `Partial physically`
- Owns:
  - proposal submission
  - submission completeness
  - duplicate submission prevention
  - submitted-proposal immutability
- Technical mapping today:
  - `apps/marketplace/models.py::Application`

### Evaluation

- Status: `Implemented`
- Owns:
  - transition into evaluation
  - evaluation-team governance
  - criterion assessments
  - proposal comparison summaries
  - comparative ranking for adjudication support
  - award decision
  - award snapshot traceability
  - persisted challenge evaluation timeline
- Technical mapping:
  - `apps/evaluation/`

### Notifications

- Status: `Implemented`
- Owns:
  - internal notifications
  - unread/read state
  - inbox consumption of evaluation events
- Technical mapping:
  - `apps/notifications/`

### Platform Administration

- Status: `Implemented`
- Owns:
  - technical governance
  - cross-context administration
  - superuser safeguards

## Core Domain Objects

### Organizacion

- Status: `Implemented`
- Technical mapping: `corporate.Organization`
- Key semantics:
  - has unique tax identifier
  - adopts exactly one current market role
  - can publish or apply depending on role

### Desafio

- Status: `Implemented`
- Technical mapping: `marketplace.Challenge`
- Aggregate semantics:
  - published by one `Solicitante`
  - has lifecycle state
  - may define application deadline
  - must define evaluation criteria before entering `Evaluacion`

### Criterio de evaluacion

- Status: `Implemented`
- Technical mapping: `marketplace.ChallengeEvaluationCriterion`
- Semantics:
  - belongs to one `Desafío`
  - is explicitly ordered by `position`
  - currently has no weight/ponderation model

### Propuesta

- Status: `Implemented`
- Technical mapping: `marketplace.Application`
- Aggregate semantics:
  - belongs to one `Desafío`
  - submitted by one `Proveedor tecnológico`
  - must include structured required components
  - becomes immutable after submission

### Evaluacion de criterio

- Status: `Implemented`
- Technical mapping: `evaluation.ApplicationCriterionEvaluation`
- Semantics:
  - belongs to one `Propuesta`
  - targets one challenge criterion
  - records score, comment, evaluator, and timestamp
  - allows one current persisted evaluation per `(application, criterion, evaluator)`
  - supports multiple independent evaluators on the same criterion

### Decision de adjudicacion

- Status: `Implemented`
- Technical mapping: `evaluation.AwardDecision`
- Semantics:
  - one per `Desafío` at most
  - selects one winning `Propuesta`
  - requires rationale/comment
  - persists a snapshot of the winning proposal evaluation state

### Snapshot de adjudicacion

- Status: `Implemented`
- Technical mapping:
  - fields on `evaluation.AwardDecision`
- Semantics:
  - preserves total score
  - preserves average score
  - preserves evaluated criteria count
  - preserves total criteria count
  - preserves registered assessment count
  - preserves overall and eligible ranking positions
  - exists for later traceability even if read models evolve

### Evento de historial del desafio

- Status: `Implemented`
- Technical mapping: `evaluation.ChallengeTimelineEntry`
- Semantics:
  - persisted projection of important evaluation milestones
  - currently stores:
    - evaluation started
    - application evaluated
    - challenge awarded

### Notificacion interna

- Status: `Implemented`
- Technical mapping: `notifications.Notification`
- Semantics:
  - delivered to one representative
  - has kind, title, body, link, and read state
  - currently fed by evaluation events

## Read Models and Derived Concepts

These concepts are part of the ontology even when they are not first-class persisted aggregates.

### Resumen de evaluacion de propuesta

- Status: `Implemented`
- Technical mapping:
  - `apps/evaluation/application/queries.py::ApplicationEvaluationSummary`
- Semantics:
  - evaluated criteria count
  - criteria total
  - completion status
  - registered assessment count
  - total score
  - average score
  - criterion-by-criterion detail
  - per-criterion evaluation count and average
  - per-evaluator audit detail

### Ranking comparativo de propuestas

- Status: `Implemented`
- Technical mapping:
  - built in `apps/evaluation/application/queries.py`
- Semantics:
  - orders proposals for publisher-facing comparison
  - prioritizes complete evaluations
  - then stronger average score
  - then total score
  - then registered assessment count
  - then primary key as deterministic tie-breaker
- Note:
  - this is ranking, not weighted scoring

## Permission Model

### Publishing and submission

- Only a `Solicitante` can publish a `Desafío`
- Only a `Proveedor tecnológico` can submit a `Propuesta`
- Status: `Implemented`

### Evaluation-team management

- Only the publisher organization can define the evaluation team for its challenge
- Evaluation-team members must belong to the publisher organization
- Exactly one designated adjudicator is allowed per challenge
- At least one designated evaluator and one designated adjudicator are required before evaluation starts
- The same representative may simultaneously be evaluator and adjudicator if the publisher organization decides so
- Status: `Implemented`

### Evaluation execution

- Only the publisher organization can start evaluation
- Only a designated evaluator can register criterion assessments
- Only the designated adjudicator can adjudicate
- Observers do not currently receive mutation permissions
- Status: `Implemented`

## Lifecycle and State Semantics

### Desafio lifecycle

- Status: `Implemented`
- Technical mapping: `marketplace.Challenge.Status`
- States:
  - `DRAFT`
  - `PUBLISHED`
  - `CLOSED`
  - `UNDER_EVALUATION`
  - `AWARDED`
  - `ARCHIVED`

### Propuesta lifecycle

- Status: `Partial`
- Current semantics:
  - structured proposal submitted once
  - immutable after submission
- Missing:
  - explicit persisted draft state

### Notificacion lifecycle

- Status: `Implemented`
- States:
  - unread
  - read

## Domain Events and Traceability

### ChallengeEvaluationStarted

- Status: `Implemented`
- Emitted when:
  - a challenge moves from `PUBLISHED` to `UNDER_EVALUATION`
- Consumers today:
  - challenge timeline persistence
  - internal notifications

### ApplicationEvaluationRecorded

- Status: `Implemented`
- Emitted when:
  - criterion-by-criterion proposal evaluation is registered
- Carries:
  - applicant and publisher references
  - blind proposal reference
  - score totals
  - completion counters
  - assessment count
  - ranking positions
- Consumers today:
  - challenge timeline persistence
  - applicant notifications
  - evaluation-team notifications

### ChallengeAwarded

- Status: `Implemented`
- Emitted when:
  - an award decision is recorded
- Consumers today:
  - challenge timeline persistence
  - internal notifications

## Semantic Relationships

- One `Organización` can publish many `Desafíos` if it is a `Solicitante`
- One `Organización` can submit many `Propuestas` if it is a `Proveedor tecnológico`
- One `Desafío` can receive many `Propuestas`
- One `Desafío` owns many `Criterios de evaluación`
- One `Propuesta` can have many persisted criterion assessments, but at most one current assessment per `(criterion, evaluator)`
- One `Desafío` can have many evaluation-role assignments
- One `Desafío` can have at most one `Decision de adjudicación`
- One `Decision de adjudicación` selects exactly one winning `Propuesta`
- Evaluation events may produce persisted timeline entries and notifications

## Implemented Invariants

- Unique organization tax identifier
- Unique representative username and email
- Single market role per organization in the current model
- Role-restricted challenge publication
- Role-restricted proposal submission
- No duplicate proposal per challenge/applicant
- Submission allowed only while a challenge is open
- Explicit challenge lifecycle
- Structured proposal completeness before submission
- Submitted proposal immutability
- Evaluation criteria required before evaluation starts
- Award eligibility requires criterion coverage
- Evaluation team required before evaluation starts
- Evaluation roles restricted to publisher-organization members
- Only designated evaluators may score
- Only designated adjudicator may adjudicate
- At most one adjudicator per challenge
- At most one award decision per challenge
- Applicant identity remains blind until award
- At most one current assessment per `(proposal, criterion, evaluator)`
- Award decision preserves an evaluation snapshot

## Explicitly Implemented But Still Semantically Limited

### Blind evaluation

- Status: `Implemented`
- Semantics:
  - applicant identity remains hidden during publisher-facing evaluation and adjudication flows
  - blind references are used instead of applicant names until adjudication is registered
  - applicant identity becomes visible again after adjudication
- Enforcement today:
  - blind read models
  - blind form labels
  - blind evaluation/adjudication templates
  - challenge timeline descriptions without applicant identity leakage before award

### Multiple independent evaluators per criterion

- Status: `Implemented`
- Semantics:
  - different designated evaluators may each register their own current assessment for the same criterion
  - the same evaluator updates its current assessment instead of producing a second active row
  - proposal aggregates are computed across all registered current assessments
  - adjudication eligibility depends on criterion coverage, not on every evaluator scoring every criterion

### Weighted criteria

- Status: `Planned`
- Current limitation:
  - criteria have ordering, not weighting
- Consequence:
  - ranking is comparative but not weighted by criterion importance

### Physical bounded-context separation

- Status: `Partial`
- Current limitation:
  - `Challenge` and `Application` remain physically colocated inside `apps/marketplace/`
- Consequence:
  - conceptual boundaries are clearer than code boundaries

## Canonical Review Rule

A change should be questioned if it introduces code, documentation, or UI behavior that conflicts with any of the following without an explicit ADR or ontology update:

- market roles are distinct from evaluation-governance roles
- evaluation permissions are explicit, not implicit
- challenge, application, evaluation, and notifications remain distinct conceptual contexts
- adjudication remains traceable through a persisted decision plus snapshot
- major evaluation milestones remain event-emitting and auditable
