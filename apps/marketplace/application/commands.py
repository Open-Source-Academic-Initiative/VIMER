from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional


@dataclass(frozen=True)
class PublishChallengeCommand:
    title: str
    description: str
    evaluation_criteria: str = ""
    application_deadline: Optional[date] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: str = "COP"
    category_ids: tuple[int, ...] = ()
    attachments: tuple[Any, ...] = ()


@dataclass(frozen=True)
class SubmitApplicationCommand:
    problem_understanding: str
    proposed_solution: str
    capabilities_evidence: str
    execution_plan: str
    offered_amount: Optional[Decimal] = None
    offer_currency: str = ""
    estimated_duration_days: Optional[int] = None
    attachments: tuple[Any, ...] = ()


@dataclass(frozen=True)
class SaveApplicationDraftCommand:
    problem_understanding: str = ""
    proposed_solution: str = ""
    capabilities_evidence: str = ""
    execution_plan: str = ""
    offered_amount: Optional[Decimal] = None
    offer_currency: str = ""
    estimated_duration_days: Optional[int] = None
    attachments: tuple[Any, ...] = ()
