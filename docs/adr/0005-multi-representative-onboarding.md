# ADR 0005: Multi-Representative Onboarding with Delegable Titularity

## Status

Accepted

## Context

VIMER's current model exposes one `User` (representative) per `Organization` through a flat foreign key. Public self-service signup is the chosen onboarding posture for the first release, which means that a second representative of an organization that is already registered cannot enter the platform: the unique tax identifier blocks them, and there is no mechanism that lets them attach to the existing organization aggregate.

Real organizations almost always have more than one operating member. Without a way to onboard additional representatives, the platform forces either credential sharing or operational stalls. Both are unacceptable.

## Decision

VIMER introduces three concepts on top of the existing `Identity` and `Corporate` contexts:

- `Representante titular` — the first representative registered for an organization is automatically marked as its titular. The titular is the holder of governance over its organization on the platform.
- `Solicitud de unión` — when a representative self-registers using a tax identifier already associated with an existing organization, the registration succeeds but the representative enters a `PENDING_APPROVAL` state. A pending join request is created, addressed to the organization's titular.
- `Transferencia de titularidad` — the current titular can transfer the role to any other active representative of the same organization. The transfer is a single auditable action and produces a domain event.

Approval rules:

- only the current titular may approve or reject pending join requests for its organization
- a rejected representative cannot operate but the rejection itself is preserved for audit
- a pending request expires after a configurable window (default 14 days) and is closed automatically
- the titular receives an internal notification and an email when a new request arrives
- the requesting representative receives an internal notification and an email when their request is approved, rejected, or expired

Domain events emitted (consumed by `Notifications` and the audit timeline):

- `RepresentativeJoinRequested`
- `RepresentativeJoinApproved`
- `RepresentativeJoinRejected`
- `RepresentativeJoinExpired`
- `OrganizationOwnershipTransferred`

Invariants introduced:

- one and only one active titular per organization at any time
- titularity can only be held by an active representative of the same organization
- approval/rejection of join requests requires titular role at the time of action
- titularity transfer requires the current titular as actor and an active target representative

## Consequences

Positive:

- the platform supports realistic organizations with multiple operating members
- governance is explicit and auditable instead of implicit
- the single-point-of-failure of an unreachable titular is mitigated by transferable titularity
- the new flows compose cleanly with the existing `Notifications` context through events

Negative:

- the `Identity` context grows: new states on `User`, new `OrganizationJoinRequest` aggregate, new templates, new email content
- automated tests must cover the new state machine and the cross-representative authorization rules
- the recovery path for an unreachable titular still depends on `Administrador de plataforma` action through Django Admin (covered in ADR 0009)

## Follow-Up

- model `OrganizationJoinRequest` with `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED` states
- model titularity as a flag on `User` (`is_organization_titular`) backed by a database constraint that enforces at most one active titular per organization
- expose titularity transfer through a dedicated view, not generic admin UI
- add new invariants `INV-50` through `INV-55` to `docs/domain/invariants.md`
- extend `docs/domain/ontology_v4.md` with `Representante titular`, `Solicitud de unión` and the related events
