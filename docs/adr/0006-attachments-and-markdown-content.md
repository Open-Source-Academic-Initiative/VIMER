# ADR 0006: Attachments and Sanitized Markdown in Challenge and Proposal Content

## Status

Accepted

## Context

The current product carries `Desafío` and `Propuesta` content as plain-text fields. The proposal aggregate already has four mandatory structured components (`problem_understanding`, `proposed_solution`, `capabilities_evidence`, `execution_plan`), but these remain plain text without formatting and without any way to attach a richer artifact such as a PDF technical brief, a deck, or supporting evidence imagery.

Real R&D&I challenges and proposals are not plain text. Forcing participants to flatten everything into prose pushes them to share material out of band (Drive links, email), which fragments traceability and undermines the audit trail that `Evaluation` was designed to keep.

## Decision

VIMER will support two complementary content enrichments on both `Desafío` and `Propuesta`:

- file attachments
- sanitized markdown in long-form text fields

### Attachments

- new aggregates: `ChallengeAttachment` and `ApplicationAttachment`
- per-entity caps configurable through environment (defaults: 5 attachments per entity, 10 MB each)
- MIME allowlist enforced server-side: `application/pdf`, `image/jpeg`, `image/png`
- file extension and MIME are both validated; mismatches are rejected
- filenames are normalized server-side and a stable opaque identifier is used in URLs
- attachments are persisted through Django `STORAGES` and remain on the local filesystem during the pilot; production may migrate to object storage without changing call sites

### Markdown

- markdown is supported in long-form fields (`Desafío.description`, the four mandatory `Propuesta` components)
- markdown is rendered server-side using the `markdown` library
- the rendered output is sanitized using `bleach` with a conservative allowlist:
  - tags: paragraphs, headings up to `h3`, lists, blockquote, emphasis, strong, code, pre, links
  - attributes: `href` on links only, restricted to `http`/`https`/`mailto` schemes
  - no inline styles, no scripts, no iframes, no images embedded by markdown
- raw HTML in markdown source is escaped, not rendered

### Blind-evaluation preservation

The existing blind-evaluation rules (see `INV-26` and `apps/evaluation/domain/blind_references.py`) extend to attachments:

- attachment filenames presented to evaluators must not leak applicant identity until adjudication
- attachments uploaded on a `Propuesta` are accessible only to the applicant organization, the evaluation team of that challenge, and the publisher organization after adjudication
- attachments uploaded on a `Desafío` are public to all authenticated representatives once the challenge is published

### Storage and access

- download URLs are routed through Django views, not direct media URLs, so permission checks always run
- the existing `media/` directory layout remains the pilot default; ADR 0004's `DEPLOYMENT_PROFILE` does not require object storage in pilot mode

## Consequences

Positive:

- the proposal becomes a credible technical document rather than a flat textarea
- audit and adjudication traceability improves, since evidence lives on the platform
- markdown gives publishers a way to communicate complex challenges without leaving the platform
- the sanitization pipeline keeps the attack surface manageable

Negative:

- the codebase gains two new models, file validators, and permission-aware download views
- markdown rendering must be reviewed against the existing CSP (`unsafe-inline` for style is currently allowed; markdown does not use inline styles, so CSP can stay as-is for this release)
- file storage in `media/` complicates pilot backups, which ADR 0009 explicitly does not implement
- migration to object storage in production is a follow-up, not a release task

## Follow-Up

- add `python-markdown` and `bleach` to `requirements.txt`
- model `ChallengeAttachment` and `ApplicationAttachment` with size, MIME, original filename, opaque identifier, and ownership FK
- add `INV-56` through `INV-59` to `docs/domain/invariants.md` for MIME allowlist, size cap, blind preservation on attachments, and markdown sanitization output
- extend the proposal forms and templates to support upload, listing, and removal of attachments
- extend the evaluation read models so attachment metadata respects blind references
