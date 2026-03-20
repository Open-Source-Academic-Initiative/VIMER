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

### INV-15

Rule:

- A Desafío can have at most one winning Propuesta in adjudication.

Status:

- `Implemented`

Current enforcement:

- `AwardDecision` one-to-one relation to `Challenge`
- adjudication service validation
- evaluation flow and service tests

## Near-Term Enforcement Priorities

The next invariants to implement in code should be:

1. translate evaluation outcomes to richer domain events

## Traceability Expectation

Every invariant should eventually map to:

1. a documented business rule
2. an application-service or domain-rule implementation
3. persistence enforcement when appropriate
4. at least one automated test
