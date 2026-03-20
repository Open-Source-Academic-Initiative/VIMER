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

- Not implemented yet as its own module or app.

Notes:

- This is part of the target core domain and should become explicit in code.

### Decisión de adjudicación

Business meaning:

- Explicit decision selecting a winning proposal or closing evaluation with rationale.

Current technical mapping:

- Not implemented yet.

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
- `Administración de plataforma`
