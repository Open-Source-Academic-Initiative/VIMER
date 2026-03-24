from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ChallengeEvaluationStarted:
    challenge_id: int
    publisher_organization_id: int
    started_by_user_id: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ChallengeAwarded:
    challenge_id: int
    publisher_organization_id: int
    winning_application_id: int
    award_decision_id: int
    decided_by_user_id: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class ApplicationEvaluationRecorded:
    challenge_id: int
    application_id: int
    applicant_organization_id: int
    publisher_organization_id: int
    evaluated_by_user_id: int
    evaluated_count: int
    criteria_total: int
    total_score: int
    average_score: float | None
    ranking_position: int | None
    eligible_ranking_position: int | None
    occurred_at: datetime
