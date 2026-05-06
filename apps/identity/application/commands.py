from dataclasses import dataclass
from typing import Any

from apps.corporate.models import Organization


@dataclass(frozen=True)
class RegisterOrganizationUserCommand:
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    tax_id: str
    business_name: str
    chamber_of_commerce_record: str
    role: Organization.MarketRole
    contact_phone: str
    logo_upload: Any = None
    accepted_terms: bool = True
    accepted_privacy_policy: bool = True
    turnstile_token: str = ""


@dataclass(frozen=True)
class DecideOrganizationJoinRequestCommand:
    join_request_id: int


@dataclass(frozen=True)
class TransferOrganizationTitularityCommand:
    target_user_id: int
