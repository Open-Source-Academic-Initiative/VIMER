# ADR 0008: Pilot Launch Posture — Jurisdiction, Monetization, Support

## Status

Accepted

## Context

The first official release of VIMER is bounded as a closed pilot. Several adjacent product, legal and operational dimensions need to be locked together so that downstream technical decisions stay coherent.

Three of those dimensions are decided here as a single posture, because each one constrains the others:

- distribution model and onboarding
- jurisdiction and compliance scope
- monetization and support

## Decision

The first release is shipped as a controlled pilot with the following posture:

### Distribution and onboarding

- the production-grade public signup flow is the only entry point; there is no invitation-token gate
- the URL of the deployed instance is distributed only to the participating organizations of the pilot, by the operator, through external channels
- new representatives self-register and join their organization through the multi-representative flow defined in ADR 0005
- the public signup is protected by Cloudflare Turnstile against automated abuse
- mandatory acceptance of T&C and Política de Tratamiento at signup is enforced server-side

### Jurisdiction and compliance scope

- jurisdiction: Colombia
- compliance baseline: Habeas Data (Ley 1581 de 2012, Decreto 1377 de 2013)
- compliance posture: minimum legal at signup
  - explicit acceptance of versioned T&C and Política de Tratamiento de Datos Personales as a prerequisite to register
  - identification of the responsible party (`Responsable del Tratamiento`) inside the Política
  - support email visible in the policy as the channel for ARCO+ rights (acceso, rectificación, cancelación, oposición, revocación)
  - no in-platform self-service flow for data export or account deletion in this release
- RGPD and other extra-territorial frameworks are explicitly out of scope

### Monetization

- the pilot operates free of charge for all participants
- no payment integration, no plans, no billing, no DIAN electronic invoicing in this release
- VIMER acts as a matchmaking platform only; it is not a party to any contract that may result from an adjudicated challenge
- the T&C state explicitly that VIMER does not intervene in the relationship between `Solicitante` and `Proveedor tecnológico` after `AWARDED`

### Support

- a single support email is exposed in the application footer and inside the Política de Tratamiento
- a FAQ page is published as a static template with an initial set of questions agreed with the pilot operator
- support tickets are not modeled in the application; correspondence happens by email
- response targets are documented operationally but not contractually

## Consequences

Positive:

- the legal, financial and operational surface of the release is sharply bounded
- no payment integration, billing, multi-currency, KYC, or RGPD work is required
- the pilot can run on a single VPS with the dual-mode topology defined in ADR 0004

Negative:

- the public signup flow is exposed to the open internet; Turnstile mitigates but does not eliminate abuse
- the Habeas Data minimum still requires drafted legal documents that are not engineering deliverables
- support load depends on the operator's discipline; without ticket modeling, traceability of complaints is informal

## Follow-Up

- author `T&C VIMER v1` and `Política de Tratamiento de Datos VIMER v1` in Spanish
- publish both documents as static template pages and link them from the signup form and footer
- add a checkbox on the signup form that records acceptance with the document version identifier
- model the version of accepted documents on the `User` aggregate so future revisions can require re-acceptance
- expose a FAQ page seeded with 10–20 questions covering signup, organization roles, challenge publication, proposal submission, evaluation lifecycle and support channels
- add the support email to the footer template and to the Política de Tratamiento as the ARCO+ contact
