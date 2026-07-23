from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ChallengeLifecycleChanged:
    challenge_id: int
    event_type: str
    actor_user_id: int | None
    occurred_at: datetime
