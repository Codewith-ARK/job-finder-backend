from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DbSession

from ..config import get_settings
from ..models import Agency, Membership, ReferralLink, User
from ..models.common import utcnow
from ..schemas.referrals_schema import (
    ReferralCreatedOut,
    ReferralCreateInput,
    ReferralLinkOut,
    ReferralResolveOut,
)
from .credentials import hash_secret, new_secret
from .errors import Conflict, Forbidden, NotFound

STAFF_ROLES = ("employee", "supervisor")


def _status(link: ReferralLink, now) -> str:
    if link.revoked_at is not None:
        return "revoked"
    if link.used_at is not None:
        return "used"
    if link.expires_at <= now:
        return "expired"
    return "active"


def _status_reason(status: str) -> str:
    return {
        "used": "This referral link has already been used.",
        "expired": "This referral link has expired.",
        "revoked": "This referral link was revoked.",
        "inactive": "This referral link is no longer accepting signups.",
    }.get(status, "")


def _referrer_active(db: DbSession, link: ReferralLink) -> bool:
    """The link is only usable while its creator still works in that agency."""
    creator = db.get(User, link.created_by)
    if not creator or not creator.is_active or creator.role not in STAFF_ROLES:
        return False
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == creator.id,
            Membership.agency_id == link.agency_id,
            Membership.active.is_(True),
        )
    )
    return membership is not None


def _eligibility_reason(db: DbSession, link: ReferralLink) -> str | None:
    if not link.agency or link.agency.status != "active":
        return "That agency is not currently accepting referrals."
    if not _referrer_active(db, link):
        return "This referral link is no longer accepting signups."
    return None


def _link_out(link: ReferralLink) -> ReferralLinkOut:
    return ReferralLinkOut(
        id=link.id,
        label=link.label,
        token_hint=link.token_hint,
        agency_name=link.agency.name if link.agency else "",
        created_by_name=link.creator.name if link.creator else "",
        status=_status(link, utcnow()),
        expires_at=link.expires_at,
        created_at=link.created_at,
        used_at=link.used_at,
        revoked_at=link.revoked_at,
    )


def _by_token(db: DbSession, token: str) -> ReferralLink | None:
    token = token.strip()
    if not token:
        return None
    return db.scalar(select(ReferralLink).where(ReferralLink.token_hash == hash_secret(token)))


def resolve(db: DbSession, token: str) -> ReferralResolveOut:
    """Describe a referral link without consuming it."""
    link = _by_token(db, token)
    if not link:
        return ReferralResolveOut(
            valid=False,
            status="unknown",
            reason="This referral link is not valid.",
        )
    status = _status(link, utcnow())
    inactive_reason = _eligibility_reason(db, link) if status == "active" else None
    if inactive_reason:
        status = "inactive"
    return ReferralResolveOut(
        valid=status == "active",
        status=status,
        agency_name=link.agency.name if link.agency else "",
        referrer_name=link.creator.name if link.creator else "",
        label=link.label,
        expires_at=link.expires_at,
        reason=inactive_reason or _status_reason(status),
    )


def consume(db: DbSession, token: str, user_id: str) -> ReferralLink:
    """Atomically mark a referral link as used by exactly one account.

    The conditional UPDATE is the single-use guarantee. If another request consumes
    the link first, this update touches zero rows and the caller rolls back.
    """
    link = _by_token(db, token)
    if not link:
        raise Conflict("This referral link is not valid.")
    inactive_reason = _eligibility_reason(db, link)
    if inactive_reason:
        raise Conflict(inactive_reason)
    now = utcnow()
    result = db.execute(
        update(ReferralLink)
        .where(
            ReferralLink.id == link.id,
            ReferralLink.used_at.is_(None),
            ReferralLink.revoked_at.is_(None),
            ReferralLink.expires_at > now,
        )
        .values(used_at=now, used_by=user_id)
    )
    if result.rowcount != 1:
        db.rollback()
        raise Conflict("This referral link has already been used or has expired.")
    db.refresh(link)
    return link


def _active_membership(db: DbSession, agency_id: str, user: User) -> Membership:
    membership = db.scalar(
        select(Membership).where(
            Membership.agency_id == agency_id,
            Membership.user_id == user.id,
            Membership.active.is_(True),
        )
    )
    if not membership:
        raise Forbidden("You are not an active member of this agency.")
    return membership


def create_link(
    db: DbSession, agency: Agency, actor: User, payload: ReferralCreateInput
) -> ReferralCreatedOut:
    if actor.role not in STAFF_ROLES:
        raise Forbidden("Only agency agents and supervisors can create referral links.")
    _active_membership(db, agency.id, actor)
    token = new_secret()
    link = ReferralLink(
        agency_id=agency.id,
        created_by=actor.id,
        token_hash=hash_secret(token),
        token_hint=token[:8],
        label=payload.label.strip(),
        expires_at=utcnow() + timedelta(days=payload.expires_in_days),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return ReferralCreatedOut(link=_link_out(link), token=token, path=f"/join/{token}")


def list_links(db: DbSession, agency: Agency, actor: User) -> list[ReferralLinkOut]:
    _active_membership(db, agency.id, actor)
    query = select(ReferralLink).where(ReferralLink.agency_id == agency.id)
    if actor.role != "supervisor":
        query = query.where(ReferralLink.created_by == actor.id)
    links = db.scalars(
        query.order_by(ReferralLink.created_at.desc()).limit(
            get_settings().max_workspace_items
        )
    )
    return [_link_out(link) for link in links]


def revoke_link(
    db: DbSession, agency: Agency, actor: User, link_id: str
) -> list[ReferralLinkOut]:
    _active_membership(db, agency.id, actor)
    link = db.get(ReferralLink, link_id)
    if not link or link.agency_id != agency.id:
        raise NotFound("That referral link was not found.")
    if actor.role != "supervisor" and link.created_by != actor.id:
        raise Forbidden("You can only revoke your own referral links.")
    if link.used_at is not None:
        raise Conflict("A used referral link cannot be revoked.")
    if link.revoked_at is None:
        link.revoked_at = utcnow()
        db.commit()
    return list_links(db, agency, actor)


def context_for_candidate(db: DbSession, candidate_id: str):
    """Return the agency/referrer that created this candidate, if any."""
    link = db.scalar(
        select(ReferralLink).where(ReferralLink.used_by == candidate_id).limit(1)
    )
    if not link:
        return None
    return {
        "agency_name": link.agency.name if link.agency else "",
        "referrer_name": link.creator.name if link.creator else "",
        "label": link.label,
    }
