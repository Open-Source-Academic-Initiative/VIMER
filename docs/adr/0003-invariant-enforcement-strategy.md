# ADR 0003: Invariant Enforcement Strategy

## Status

Accepted

## Context

Important business rules already exist in the current MVP, but enforcement is spread across:

- forms
- views
- application services
- model validation
- database constraints

This is useful pragmatically, but difficult to reason about as a domain model unless the invariants are named and traced explicitly.

## Decision

VIMER will enforce important invariants in multiple layers, with explicit ownership:

1. domain or application rule modules describe the rule
2. application services orchestrate the rule in write flows
3. model validation acts as a safety net for entity consistency
4. database constraints enforce persistence-level integrity when appropriate
5. web-layer checks improve user feedback but do not replace domain enforcement

## Consequences

Positive:

- reduces single-point-of-failure validation
- improves traceability from business rule to code
- enables safer refactors

Negative:

- some rules may appear in more than one layer
- discipline is required to keep the layers aligned

## Enforcement Heuristic

Use:

- web layer for UX feedback and coarse access control
- application services for use-case orchestration
- domain rules for business meaning
- model validation for local entity consistency
- database constraints for non-negotiable integrity

## Follow-Up

- add explicit domain rule modules in `apps/marketplace/`
- map documented invariants to tests
- track planned invariants before implementing new lifecycle features
