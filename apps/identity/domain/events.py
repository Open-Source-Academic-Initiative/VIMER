from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RepresentativeJoinRequested:
    join_request_id: int
    organization_id: int
    requester_user_id: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class RepresentativeJoinApproved:
    join_request_id: int
    organization_id: int
    requester_user_id: int
    decided_by_user_id: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class RepresentativeJoinRejected:
    join_request_id: int
    organization_id: int
    requester_user_id: int
    decided_by_user_id: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class RepresentativeJoinExpired:
    join_request_id: int
    organization_id: int
    requester_user_id: int
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OrganizationOwnershipTransferred:
    organization_id: int
    previous_titular_user_id: int
    new_titular_user_id: int
    transferred_by_user_id: int
    occurred_at: datetime
