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
