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

### Administración de plataforma

Business meaning:

- Operational and governance responsibilities of the platform itself.

Current technical mapping:

- Django admin, superuser capabilities, operational conventions.

Notes:

- This is not a market role.
- Do not mix it with `Solicitante` or `Proveedor tecnológico`.

## Technical Legacy Terms

These terms are acceptable in code while the migration is incomplete, but should be treated as technical debt when they appear outside technical internals.

### `Challenge`

- Technical persistence and module name for `Desafío`.

### `Application`

- Technical persistence and module name for `Propuesta`.
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
- `Desafío`
- `Propuesta`
- `Evaluación`
- `Evaluador designado`
- `Adjudicador designado`
- `Observador de evaluacion`
- `Evento de historial del desafio`
- `Notificacion interna`
- `Administración de plataforma`
