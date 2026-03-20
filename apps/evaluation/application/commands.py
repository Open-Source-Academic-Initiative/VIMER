from dataclasses import dataclass


@dataclass(frozen=True)
class AwardDecisionCommand:
    winning_application_id: int
    comment: str


@dataclass(frozen=True)
class CriterionAssessmentInput:
    criterion_id: int
    score: int
    comment: str


@dataclass(frozen=True)
class EvaluateApplicationCommand:
    application_id: int
    assessments: tuple[CriterionAssessmentInput, ...]
