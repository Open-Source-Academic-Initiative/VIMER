# ADR 0007: Closed Taxonomy for Challenge Categorization

## Status

Accepted

## Context

The current challenge listing is a flat chronological feed. As soon as the platform holds more than a handful of published challenges, a `Proveedor tecnológico` cannot reasonably scan everything and a `Solicitante` cannot signal what kind of challenge they are publishing. Discovery becomes the next bottleneck.

Two main approaches exist for categorization: a centrally curated catalog, or open user-defined tags. Open tags grow organically but fragment search (`AI`, `IA`, `inteligencia-artificial`, `machine-learning`) and require a normalization process that nobody owns. A curated catalog is slower to evolve but produces consistent, filterable, analyzable signal.

For a closed pilot whose primary purpose is to validate the marketplace flow, fragmentation noise is more harmful than vocabulary lag.

## Decision

VIMER adopts a closed taxonomy for challenge categorization in the first release:

- a new `Categoría` aggregate is owned by `Administración de plataforma`
- the catalog is managed exclusively through Django Admin by users with platform-administration capability
- a `Desafío` carries a many-to-many relation to `Categoría`
- at publication, the `Solicitante` selects one or more categories from the catalog; no free-text input is accepted
- the marketplace listing exposes filters by category and by lifecycle status, and a search box over title and description

The catalog ships with a small initial set seeded by data migration. Growth happens through admin action, not user input.

The marketplace search uses Django ORM `icontains` against title and description. SQLite supports it directly. Postgres and MariaDB can be upgraded later to full-text search without changing the public interface, because the surface stays a `q` query parameter.

## Consequences

Positive:

- consistent, filterable categorization from day one
- analytics on category distribution become trivial
- the `Solicitante` is guided toward thinking about classification at publication time
- search and filters compose: "categoría = AgTech AND status = PUBLISHED AND q = sensor"

Negative:

- the admin role becomes the bottleneck for vocabulary growth; a missing category requires admin action before a publisher can use it
- the initial catalog must be designed up front, not discovered
- user-driven tagging is postponed; if real product signal demands it, an additive change will be needed in a later release

## Follow-Up

- model `Categoría` with `name`, `slug`, `description`, `is_active`, `position`
- ship a data migration with an initial catalog of categories agreed with the pilot stakeholders
- expose category management in Django Admin with reordering and soft-disable
- add a category multi-select to the challenge publication form and the challenge edit form (where edit is allowed)
- extend the marketplace listing template to render filters and a search box
- add `INV-60` and `INV-61` to `docs/domain/invariants.md`: a published challenge must have at least one category, and a category in use cannot be hard-deleted
