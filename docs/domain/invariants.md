# VIMER Domain Invariants

## Purpose

This document records domain invariants and tracks whether they are:

- implemented in code
- partially implemented
- planned

It is meant to connect business intent with concrete enforcement in:

- web flows
- application services
- model validation
- database constraints
- tests

For the canonical cross-document domain model, see `docs/domain/ontology_v4.md`.

## Status Legend

- `Implemented`: enforced in the current codebase
- `Partial`: present but incomplete or only enforced in some layers
- `Planned`: documented target, not yet implemented

## Invariant Inventory

### INV-01

Rule:

- An organization must have a unique tax identifier.

Status:

- `Implemented`

Current enforcement:

- model uniqueness
- registration flow validation

### INV-02

Rule:

- A representative account must use a unique email address.

Status:

- `Implemented`

Current enforcement:

- user model uniqueness
- registration flow validation
- registration service duplicate handling

### INV-03

Rule:

- A representative account must use a unique username.

Status:

- `Implemented`

Current enforcement:

- user model uniqueness
- registration flow validation
- registration service duplicate handling

### INV-04

Rule:

- An organization adopts exactly one market role in the current model.

Status:

- `Implemented`

Current enforcement:

- single `role` field on `Organization`

Notes:

- Future multi-role support would require an explicit redesign.

### INV-05

Rule:

- Only a Solicitante organization can publish a Desafío.

Status:

- `Implemented`

Current enforcement:

- role-aware access control in web flow
- model validation on `Challenge`

### INV-06

Rule:

- Only a Proveedor tecnológico organization can submit a Propuesta.

Status:

- `Implemented`

Current enforcement:

- role-aware access control in web flow
- model validation on `Application`

### INV-07

Rule:

- A Proveedor tecnológico can submit at most one Propuesta per Desafío.

Status:

- `Implemented`

Current enforcement:

- application service duplicate detection
- database unique constraint

### INV-08

Rule:

- A platform superuser cannot delete itself through platform administration.

Status:

- `Implemented`

Current enforcement:

- Django admin delete permission override
- Django admin bulk delete safeguard

### INV-09

Rule:

- Organization branding uploaded during signup must be a valid PNG or JPG image.

Status:

- `Implemented`

Current enforcement:

- form validation
- image utility validation

### INV-10

Rule:

- When no custom organization logo is uploaded, the platform must generate a default organization avatar.

Status:

- `Implemented`

Current enforcement:

- registration application service

### INV-11

Rule:

- A Desafío should only accept Propuestas while it is open for submission.

Status:

- `Implemented`

Current enforcement:

- challenge status and deadline on `Challenge`
- domain rule before submission
- model validation on `Application`
- flow and service tests

### INV-12

Rule:

- A Desafío should have an explicit lifecycle state.

Status:

- `Implemented`

Current enforcement:

- `Challenge.status` with explicit choices
- validation rules tied to publication and submission behavior

### INV-13

Rule:

- A Propuesta should contain all required business components before final submission.

Status:

- `Implemented`

Current enforcement:

- structured proposal fields on `Application`
- application service completeness rule before save
- model validation on required components
- flow and service tests

### INV-14

Rule:

- A submitted Propuesta should be immutable or only editable through explicit lifecycle rules.

Status:

- `Implemented`

Current enforcement:

- model-level immutability check after first save
- service and model tests for attempted post-submission edits

### INV-40

Rule:

- A Propuesta should have an explicit persisted lifecycle state.

Status:

- `Implemented`

Current enforcement:

- `Application.status` with `DRAFT` and `SUBMITTED`
- lifecycle-aware application services for draft save and final submission
- flow, service, and model tests

### INV-41

Rule:

- A draft Propuesta can only be created or edited while the Desafío remains open for submission.

Status:

- `Implemented`

Current enforcement:

- challenge openness check before draft save and final submission
- model validation on `Application`
- flow and service tests

### INV-15

Rule:

- A Desafío can have at most one winning Propuesta in adjudication.

Status:

- `Implemented`

Current enforcement:

- `AwardDecision` one-to-one relation to `Challenge`
- adjudication service validation
- evaluation flow and service tests

### INV-16

Rule:

- A Desafío must define evaluation criteria before it can enter Evaluación.

Status:

- `Implemented`

Current enforcement:

- `Challenge.evaluation_criteria`
- `ChallengeEvaluationCriterion`
- challenge publication flow
- evaluation application service before state transition
- marketplace and evaluation tests

### INV-17

Rule:

- A winning Propuesta must have all its criteria evaluated before adjudication.

Status:

- `Implemented`

Current enforcement:

- `ApplicationCriterionEvaluation`
- evaluation application service before adjudication
- evaluation flow and service tests

### INV-18

Rule:

- A Desafío must have at least one designated evaluator and one designated adjudicator before it can enter Evaluación.

Status:

- `Implemented`

Current enforcement:

- `ChallengeEvaluationRoleAssignment`
- evaluation application service before state transition
- evaluation flow and service tests

### INV-19

Rule:

- Evaluation roles can only be assigned to representatives of the publisher organization.

Status:

- `Implemented`

Current enforcement:

- `ChallengeEvaluationRoleAssignment.clean()`
- evaluation role-assignment service validation
- model and flow tests

### INV-20

Rule:

- Only the publisher organization can manage and execute evaluation operations for its challenge.

Status:

- `Implemented`

Current enforcement:

- evaluation application service ownership checks
- evaluation-team management flow
- evaluation and marketplace tests

### INV-21

Rule:

- Only a designated evaluator can register criterion-by-criterion proposal assessments.

Status:

- `Implemented`

Current enforcement:

- evaluation application service role check
- evaluation view access control
- evaluation flow and service tests

### INV-22

Rule:

- Only the designated adjudicator can register the final award decision for a challenge.

Status:

- `Implemented`

Current enforcement:

- evaluation application service role check
- adjudication view access control
- evaluation flow and service tests

### INV-23

Rule:

- A Desafío can have at most one designated adjudicator in the current model.

Status:

- `Implemented`

Current enforcement:

- conditional database unique constraint on `ChallengeEvaluationRoleAssignment`
- model validation

### INV-24

Rule:

- An adjudication decision must preserve the winning proposal's evaluation context for later traceability.

Status:

- `Implemented`

Current enforcement:

- snapshot fields on `AwardDecision`
- adjudication application service
- evaluation flow and service tests

### INV-25

Rule:

- Major evaluation milestones must remain auditable after they occur.

Status:

- `Implemented`

Current enforcement:

- explicit evaluation domain events
- `ChallengeTimelineEntry` persistence through event consumers
- evaluation and notifications tests

### INV-26

Rule:

- Applicant identity must remain hidden in publisher-facing evaluation and adjudication flows until the challenge is adjudicated.

Status:

- `Implemented`

Current enforcement:

- blind application references in evaluation read models
- blind labels in adjudication form choices
- blind evaluation and adjudication templates
- publisher challenge-detail rendering rules before/after award
- evaluation and marketplace tests

### INV-27

Rule:

- A designated evaluator can have at most one current persisted criterion assessment per `(Propuesta, Criterio de evaluación)`.

Status:

- `Implemented`

Current enforcement:

- database unique constraint on `(application, criterion, evaluated_by)`
- evaluation application service uses `update_or_create()` for the acting evaluator
- evaluation flow and service tests

### INV-28

Rule:

- A `Propuesta` becomes eligible for adjudication once every challenge criterion has at least one registered assessment.

Status:

- `Implemented`

Current enforcement:

- evaluation domain rule and adjudication application service
- aggregate evaluation summaries over distinct covered criteria
- evaluation flow and service tests

### INV-29

Rule:

- In the current product phase, all challenge criteria should have equal value and no explicit weighting.

Status:

- `Implemented`

Current enforcement:

- approved product policy in `evaluation_scoring_and_award_policy.md`
- evaluation read models and ranking logic average criteria equally
- evaluation service and flow tests

### INV-30

Rule:

- If a criterion receives multiple evaluations, that criterion should contribute through its own average and not gain additional competitive weight from evaluator volume alone.

Status:

- `Implemented`

Current enforcement:

- evaluation read models aggregate by criterion average first
- adjudication service reuses the same scoring semantics
- evaluation service tests

### INV-31

Rule:

- A challenge should only be adjudicated when every active proposal has complete criterion coverage.

Status:

- `Implemented`

Current enforcement:

- adjudication service blocks while active proposals remain incomplete
- adjudication UI exposes pending blind proposal references and missing criterion counts
- evaluation service and flow tests

### INV-32

Rule:

- Incomplete proposals should be shown separately as not yet eligible instead of competing in the main ranking.

Status:

- `Implemented`

Current enforcement:

- evaluation read models distinguish complete and incomplete proposals
- publisher-facing challenge detail and adjudication views render incomplete proposals separately
- marketplace and evaluation flow tests

### INV-33

Rule:

- Real ties in the best available ranking position should remain explicit, share the same compact visible position, and be resolved by the designated adjudicator.

Status:

- `Implemented`

Current enforcement:

- evaluation ranking preserves tied compact positions
- adjudication snapshot preserves tie context
- evaluation service tests

### INV-34

Rule:

- Adjudicating outside the best available ranking position should require a structured exceptional-reason code and a mandatory free-text justification.

Status:

- `Implemented`

Current enforcement:

- adjudication flow warns, requires confirmation, and records reason plus justification
- better-ranked proposals remain visible in the award snapshot for audit
- evaluation service and flow tests

## Near-Term Enforcement Priorities

The next invariants to implement in code should be:

1. keep `ontology_v4.md`, `glossary.md`, `context_map.md`, and `invariants.md` synchronized per iteration
2. preserve the implemented draft/submitted proposal lifecycle without leaking drafts into evaluation
3. deepen evaluation audit and governance beyond the current adjudication controls

## Traceability Expectation

Every invariant should eventually map to:

1. a documented business rule
2. an application-service or domain-rule implementation
3. persistence enforcement when appropriate
4. at least one automated test
