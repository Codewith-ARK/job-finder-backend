from datetime import datetime
from typing import Literal

from pydantic import Field

from .common import ApiModel

ReferralStatus = Literal["active", "used", "expired", "revoked"]


class ReferralResolveOut(ApiModel):
    valid: bool
    status: Literal["active", "used", "expired", "revoked", "unknown"]
    agency_name: str = ""
    referrer_name: str = ""
    label: str = ""
    expires_at: datetime | None = None
    reason: str = ""


class ReferralLinkOut(ApiModel):
    id: str
    label: str
    token_hint: str
    agency_name: str
    created_by_name: str
    status: ReferralStatus
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None
    revoked_at: datetime | None


class ReferralCreateInput(ApiModel):
    label: str = Field(default="", max_length=120)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class ReferralCreatedOut(ApiModel):
    link: ReferralLinkOut
    token: str
    path: str
