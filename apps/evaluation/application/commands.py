from dataclasses import dataclass


@dataclass(frozen=True)
class AwardDecisionCommand:
    winning_application_id: int
    comment: str
    exceptional_reason: str = ""
    confirm_exceptional_selection: bool = False


@dataclass(frozen=True)
class CriterionAssessmentInput:
    criterion_id: int
    score: int
    comment: str


@dataclass(frozen=True)
class EvaluateApplicationCommand:
    application_id: int
    assessments: tuple[CriterionAssessmentInput, ...]


@dataclass(frozen=True)
class AssignChallengeEvaluationRolesCommand:
    evaluator_user_ids: tuple[int, ...]
    adjudicator_user_id: int
    observer_user_ids: tuple[int, ...]
