# ADR 0001: Bounded Context Strategy

## Status

Accepted

## Context

The current codebase separates concerns into:

- `identity`
- `corporate`
- `marketplace`

This is workable for the MVP, but `marketplace` currently mixes at least two distinct domain concerns:

- challenge publication and lifecycle
- proposal submission and lifecycle

The domain direction described in the project analysis also identifies `Evaluation` and `Platform Administration` as separate concepts.

## Decision

VIMER will treat the target domain structure as:

- `Identity`
- `Corporate`
- `Challenge`
- `Application`
- `Evaluation`
- `Platform Administration`

In the short term, we will not force a full physical reorganization of Django apps.

Instead, we will:

1. keep `apps/marketplace/` as the physical Django app
2. split its internals by domain concern
3. introduce `Evaluation` as an explicit module or app when adjudication work begins

## Consequences

Positive:

- supports incremental refactoring
- reduces risk of destabilizing the MVP
- gives future work a clearer domain target

Negative:

- temporary mismatch remains between bounded contexts and physical app layout
- technical naming debt stays visible for some time

## Follow-Up

- create internal separation for challenge and proposal modules
- avoid adding new behavior to `marketplace` without assigning it to a domain concern
