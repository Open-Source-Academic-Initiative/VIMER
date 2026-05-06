# VIMER Domain Glossary

## Purpose

This glossary defines the preferred business language for VIMER.

It distinguishes:

- canonical business terms
- technical legacy names that still exist in code
- terms that should not expand further in user-facing language

## Canonical Terms

### Solicitante

Business meaning:

- Organization that publishes a challenge or need.

Current technical mapping:

- `Organization.role == DEMAND_SIDE`

Notes:

- Use `Solicitante` in product language, documentation, and tests when referring to the business role.

### Proveedor tecnológico

Business meaning:

- Organization that submits a proposal in response to a challenge.

Current technical mapping:

- `Organization.role == SUPPLY_SIDE`

Notes:

- Use `Proveedor tecnológico` in product language, documentation, and tests when referring to the business role.

### Representante

Business meaning:

- Human user operating on behalf of an organization.

Current technical mapping:

- `identity.User`

Notes:

- A representative is not a market role.
- A representative belongs to the identity context, not the marketplace core domain.

### Organización

Business meaning:

- Legal or operating entity participating in the platform.

Current technical mapping:

- `corporate.Organization`

Notes:

- An organization adopts exactly one market role in the current model.

### Desafío

Business meaning:

- Need, challenge, or opportunity published by a Solicitante.

Current technical mapping:

- `marketplace.Challenge`

Notes:

- `Challenge` is a technical legacy name.
- `Desafío` is the preferred business name.

### Propuesta

Business meaning:

- Solution submitted by a Proveedor tecnológico in response to a Desafío.

Current technical mapping:

- `marketplace.Application`

Notes:

- `Application` is a technical legacy name.
- `Propuesta` is the preferred business name.

### Evaluación

Business meaning:

- Decision-making process applied to submitted proposals.

Current technical mapping:

- `apps/evaluation/`

Notes:

- This is already explicit in code and should continue evolving as an isolated context.

### Evaluador designado

Business meaning:

- Representative explicitly assigned to score proposals criterion by criterion for one challenge.

Current technical mapping:

- `evaluation.ChallengeEvaluationRoleAssignment(role=EVALUATOR)`

Notes:

- This is not a market role.
- This role belongs to evaluation governance, not to the market itself.

### Adjudicador designado

Business meaning:

- Representative explicitly assigned to register the final award decision for one challenge.

Current technical mapping:

- `evaluation.ChallengeEvaluationRoleAssignment(role=ADJUDICATOR)`

Notes:

- This is not a market role.
- Only one designated adjudicator exists per challenge in the current implementation.

### Observador de evaluacion

Business meaning:

- Representative attached to an evaluation team for visibility and governance without direct mutation authority.

Current technical mapping:

- `evaluation.ChallengeEvaluationRoleAssignment(role=OBSERVER)`

Notes:

- This is not a market role.
- The same representative may hold more than one evaluation-governance role for the same challenge in the current implementation.

### Evento de historial del desafio

Business meaning:

- Persisted record of an important evaluation milestone in the history of a challenge.

Current technical mapping:

- `evaluation.ChallengeTimelineEntry`

### Decisión de adjudicación

Business meaning:

- Explicit decision selecting a winning proposal or closing evaluation with rationale.

Current technical mapping:

- `evaluation.AwardDecision`

### Snapshot de adjudicacion

Business meaning:

- Persisted evaluation context captured at the moment a winning proposal is adjudicated.

Current technical mapping:

- snapshot fields stored on `evaluation.AwardDecision`

### Notificacion interna

Business meaning:

- Event-driven message delivered to a representative inside the platform inbox.

Current technical mapping:

- `notifications.Notification`

### Referencia ciega de propuesta

Business meaning:

- Stable blind label used to compare and evaluate a proposal without exposing the applicant identity before adjudication.

Current technical mapping:

- blind references derived in `apps/evaluation/`

### Evaluacion vigente de criterio

Business meaning:

- Current criterion score and comment registered by one designated evaluator for one proposal.

Current technical mapping:

- `evaluation.ApplicationCriterionEvaluation`

Notes:

- The same evaluator updates this current assessment instead of creating a second active row for the same proposal and criterion.
- Different evaluators may each contribute their own current assessment for the same criterion.

### Cobertura completa de criterios

Business meaning:

- State in which a proposal has at least one registered evaluation for every challenge criterion.

Notes:

- Complete coverage is not the same as every evaluator scoring every criterion.
- In the approved scoring policy, adjudication is blocked until every active proposal has complete coverage.

### Propuesta no elegible aún

Business meaning:

- Proposal that still has pending criteria and therefore should not appear in the competitive ranking yet.

Notes:

- This is a derived evaluation status, not yet a persisted lifecycle state.

### Empate técnico

Business meaning:

- Situation in which two or more proposals share the same best available ranking outcome after the approved scoring rules are applied.

Notes:

- A technical tie should remain visible and should not be hidden by arbitrary secondary ranking signals.

### Adjudicación excepcional

Business meaning:

- Human award decision that selects a complete proposal outside the best available ranking position.

Notes:

- This requires explicit warning, structured reason, and mandatory free-text justification.

### Administración de plataforma

Business meaning:

- Operational and governance responsibilities of the platform itself.

Current technical mapping:

- Django admin, superuser capabilities, operational conventions.

Notes:

- This is not a market role.
- Do not mix it with `Solicitante` or `Proveedor tecnológico`.

## Release v1 Canonical Terms (Planned)

These terms are introduced as part of VIMER's first official release (`docs/release_plan_v1.md`). They are canonical from the moment they ship in code. Until then, any user-facing copy referencing these concepts should already use the canonical form, never an alternative.

### Representante titular

Business meaning:

- representative that holds governance over an organization on the platform.

Status:

- `Planned`

Notes:

- the first representative registered for an organization is automatically the titular.
- the titular approves or rejects pending join requests for its organization.
- the titular can transfer the role to another active representative of the same organization.
- this is not an evaluation-governance role and not a market role.

### Solicitud de unión a organización

Business meaning:

- pending request created when a representative self-registers using a tax identifier already associated with an existing organization.

Status:

- `Planned`

Notes:

- has lifecycle states `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`.
- only the current `Representante titular` of the target organization can approve or reject.
- expires automatically after a configurable window.

### Transferencia de titularidad

Business meaning:

- explicit, auditable action that moves the role of `Representante titular` from one active representative to another within the same organization.

Status:

- `Planned`

### Categoría de desafío

Business meaning:

- classification term applied to a `Desafío`, drawn from a closed catalog managed by `Administración de plataforma`.

Status:

- `Planned`

Notes:

- vocabulary is curated, not user-created.
- a published `Desafío` must reference at least one categoría.

### Adjunto de desafío

Business meaning:

- file attached to a `Desafío` to provide richer context (technical brief, supporting material).

Status:

- `Planned`

Notes:

- visible to all authenticated representatives once the challenge is published.

### Adjunto de propuesta

Business meaning:

- file attached to a `Propuesta` to provide richer evidence (technical document, deck, supporting material).

Status:

- `Planned`

Notes:

- access is restricted by ownership and by evaluation team membership.
- blind-evaluation rules extend to attachment metadata: applicant identity must not leak through filenames presented to evaluators until adjudication.

### Aceptación de documentos legales

Business meaning:

- record that links a `Representante` to the version of T&C and Política de Tratamiento de Datos accepted at signup.

Status:

- `Planned`

Notes:

- aligned with Habeas Data minimum legal posture for the pilot release.

## Technical Legacy Terms

These terms are acceptable in code while the migration is incomplete, but should be treated as technical debt when they appear outside technical internals.

### `Challenge`

- Technical persistence and module name for `Desafío`.

### `Application`

- Technical persistence and module name for `Propuesta`.
- Today it also carries the persisted `DRAFT -> SUBMITTED` lifecycle of the proposal aggregate.
- This name is especially risky because it collides with the architectural term `application layer`.

### `DEMAND_SIDE`

- Technical stored value for `Solicitante`.

### `SUPPLY_SIDE`

- Technical stored value for `Proveedor tecnológico`.

## Language Rules

1. Use canonical business terms in UI text.
2. Use canonical business terms in new versioned documentation.
3. Prefer canonical business terms in test names when the test is about domain behavior.
4. Keep technical legacy names only where needed for compatibility.
5. Do not introduce new aliases for the core market roles.

## Review Rule

A change should be questioned if it introduces new user-facing language that drifts away from:

- `Solicitante`
- `Proveedor tecnológico`
- `Representante`
- `Representante titular`
- `Desafío`
- `Propuesta`
- `Evaluación`
- `Evaluador designado`
- `Adjudicador designado`
- `Observador de evaluacion`
- `Evento de historial del desafio`
- `Notificacion interna`
- `Solicitud de unión a organización`
- `Transferencia de titularidad`
- `Categoría de desafío`
- `Adjunto de desafío`
- `Adjunto de propuesta`
- `Administración de plataforma`
