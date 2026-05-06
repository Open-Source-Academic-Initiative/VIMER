from dataclasses import dataclass
from datetime import date
from typing import Any, Optional


@dataclass(frozen=True)
class PublishChallengeCommand:
    title: str
    description: str
    evaluation_criteria: str = ""
    application_deadline: Optional[date] = None
    category_ids: tuple[int, ...] = ()
    attachments: tuple[Any, ...] = ()


@dataclass(frozen=True)
class SubmitApplicationCommand:
    problem_understanding: str
    proposed_solution: str
    capabilities_evidence: str
    execution_plan: str
    attachments: tuple[Any, ...] = ()


@dataclass(frozen=True)
class SaveApplicationDraftCommand:
    problem_understanding: str = ""
    proposed_solution: str = ""
    capabilities_evidence: str = ""
    execution_plan: str = ""
    attachments: tuple[Any, ...] = ()
