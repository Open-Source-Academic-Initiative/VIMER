from dataclasses import dataclass


@dataclass(frozen=True)
class AwardDecisionCommand:
    winning_application_id: int
    comment: str
