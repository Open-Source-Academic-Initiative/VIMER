# ADR 0002: Naming Strategy Between Business and Technical Terms

## Status

Accepted

## Context

The current codebase still uses technical legacy names such as:

- `Challenge`
- `Application`
- `DEMAND_SIDE`
- `SUPPLY_SIDE`

The business language is clearer and more aligned with the target domain model:

- `Desafío`
- `Propuesta`
- `Solicitante`
- `Proveedor tecnológico`

Immediate renaming of models and persistence artifacts would add migration and regression risk while the domain behavior is still evolving.

## Decision

VIMER will use a dual naming strategy for now:

- canonical business language in documentation, UI, and business-oriented tests
- technical legacy names in persistence and code where compatibility matters

We will not perform large technical renames until:

1. lifecycle semantics are implemented
2. invariants are explicit and tested
3. the domain boundaries are more stable

## Consequences

Positive:

- improves business clarity immediately
- reduces risk of premature refactors
- keeps the path open for later renaming

Negative:

- semantic debt remains in code internals
- developers must learn both the canonical and legacy vocabulary

## Rules

1. New user-facing copy should use canonical business terms.
2. New versioned domain docs should use canonical business terms.
3. New tests about business behavior should prefer canonical language in test names or descriptions.
4. Technical legacy names should not expand into new APIs unless necessary.

## Follow-Up

- maintain `docs/domain/glossary.md`
- revisit technical renames after `Challenge`, `Application`, and `Evaluation` stabilize
