from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..schemas.referrals_schema import (
    ReferralCreatedOut,
    ReferralCreateInput,
    ReferralLinkOut,
    ReferralResolveOut,
)
from ..security import current_staff, require_agency, require_staff
from ..services import referrals_service

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("/{token}", response_model=ReferralResolveOut)
def resolve_referral(token: str, db: DbSession = Depends(get_db)) -> ReferralResolveOut:
    """Public: describe a referral link without consuming it."""
    return referrals_service.resolve(db, token)


@router.get("", response_model=list[ReferralLinkOut])
def list_referrals(
    context=Depends(current_staff), db: DbSession = Depends(get_db)
) -> list[ReferralLinkOut]:
    return referrals_service.list_links(db, require_agency(context), context.user)


@router.post("", response_model=ReferralCreatedOut)
def create_referral(
    payload: ReferralCreateInput,
    context=Depends(require_staff),
    db: DbSession = Depends(get_db),
) -> ReferralCreatedOut:
    return referrals_service.create_link(db, require_agency(context), context.user, payload)


@router.delete("/{link_id}", response_model=list[ReferralLinkOut])
def revoke_referral(
    link_id: str,
    context=Depends(require_staff),
    db: DbSession = Depends(get_db),
) -> list[ReferralLinkOut]:
    return referrals_service.revoke_link(db, require_agency(context), context.user, link_id)
