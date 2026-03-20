from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class PublishChallengeCommand:
    title: str
    description: str
    application_deadline: Optional[date] = None


@dataclass(frozen=True)
class SubmitApplicationCommand:
    problem_understanding: str
    proposed_solution: str
    capabilities_evidence: str
    execution_plan: str
