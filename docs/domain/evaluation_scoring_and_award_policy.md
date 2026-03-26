# Evaluation Scoring and Award Policy

## Status

Approved product decision, pending implementation in code.

## Purpose

This document captures the approved functional policy for proposal scoring, ranking, ties, and adjudication.

It supersedes any assumption that more evaluator activity on the same criterion should automatically increase a proposal's competitive advantage.

## Business Goal

- Keep scoring simple, legible, and auditable.
- Ensure that all criteria have equal value in the current product phase.
- Prevent adjudication while active proposals are still partially evaluated.
- Preserve human judgment for real ties or justified exceptional decisions.

## Core Scoring Policy

- Criteria are equally important in the current product phase.
- There is no criterion weighting.
- Criterion order is used for presentation and traceability only.
- If multiple evaluators score the same criterion, that criterion's score is the average of those evaluations.
- A proposal's final score is the average of its criterion averages.

## Ranking Policy

- The same scoring logic must be used in:
  - evaluation views
  - ranking displays
  - adjudication
  - persisted adjudication snapshots
- Proposals with incomplete criterion coverage are shown separately as not yet eligible.
- Complete proposals compete in the visible ranking.
- Real ties share the same visible ranking position.
- Ranking numbering is compact:
  - if two proposals are tied in first place, the next visible position is second place

## Coverage Policy

- A proposal has complete coverage when every challenge criterion has at least one registered evaluation.
- A challenge cannot be adjudicated while any active proposal still has incomplete criterion coverage.
- If adjudication is blocked, the UI should show which blind proposal references remain pending and how many criteria are missing.

## Tie Policy

- If two or more proposals remain tied in the best available ranking position, they must be shown explicitly as tied.
- The system must not force an automatic winner when the tie persists after the approved ranking logic.
- A designated adjudicator resolves the tie through human judgment.
- The adjudication comment remains mandatory and acts as the human justification in tie scenarios.
- The persisted adjudication snapshot must preserve the fact that the winning proposal was selected from a tie.

## Award Decision Policy

- Normal rule:
  - the adjudicator should select a proposal located in the best available ranking position
- If multiple proposals are tied in the best available position:
  - the adjudicator may choose any of the tied proposals
- Exceptional rule:
  - the adjudicator may choose a different complete proposal outside the best available position
  - this requires:
    - an explicit warning
    - explicit confirmation
    - a structured reason
    - a mandatory free-text justification
    - visible disclosure of which proposals were better ranked at decision time

## Structured Reasons For Exceptional Adjudication

- `DECISION_ESTRATEGICA_EXTERNA`
- `RESTRICCION_PRESUPUESTAL_O_CONTRACTUAL`
- `RIESGO_NO_REFLEJADO_EN_EVALUACION`
- `CUMPLIMIENTO_O_REQUISITO_INSTITUCIONAL`
- `OTRO`

## Blindness And Visibility Policy

- Evaluation remains blind until adjudication, including:
  - normal ranking
  - tie scenarios
  - exceptional adjudication outside the best available ranking position
- After adjudication, the publisher may see the identity of all proposals for audit and traceability.

## Persistence And Audit Expectations

- Award snapshots should preserve:
  - winning proposal score context
  - ranking context
  - tie context when applicable
  - exceptional-adjudication reason and justification when applicable
- The audit trail should make it clear whether the final award:
  - followed the best available ranking
  - resolved a tie at the best available ranking
  - overrode the ranking through an exceptional human decision

## Implementation Note

At the time this document was approved:

- the current codebase still aggregates proposal scoring across all registered criterion assessments
- the current ranking still uses that aggregate behavior
- the approved equal-weight per-criterion policy has not yet been implemented
