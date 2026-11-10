from datetime import datetime
from typing import Literal

from .common import ApiModel

AgencyStatus = Literal["active", "pending", "suspended"]


class PlatformStatsOut(ApiModel):
    agencies: int
    users: int
    integrations: int
    health: str


class PlatformAgencyOut(ApiModel):
    id: str
    name: str
    region: str
    users: int
    status: str
    integrations: str


class IntegrationOut(ApiModel):
    id: str
    name: str
    type: str
    status: str
    last_sync: str


class AuditOut(ApiModel):
    id: str
    event: str
    detail: str
    actor: str
    created_at: datetime


class PlatformWorkspaceOut(ApiModel):
    stats: PlatformStatsOut
    agencies: list[PlatformAgencyOut]
    integrations: list[IntegrationOut]
    audit: list[AuditOut]


class AgencyStatusInput(ApiModel):
    status: AgencyStatus
