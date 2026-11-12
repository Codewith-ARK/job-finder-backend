from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..config import get_settings
from ..models import (
    Agency,
    AuthSession,
    CandidateAssignment,
    Membership,
    User,
)
from ..models.common import utcnow
from ..schemas.auth_schema import AgencyOut, DemoPersonaOut, SessionOut, SessionUserOut
from . import candidates_service, referrals_service
from .credentials import hash_password, hash_secret, new_secret, verify_password
from .errors import Conflict, Forbidden, NotFound, Unauthorized

ROLE_LABELS = {
    "candidate": "Candidate",
    "employee": "Employee",
    "supervisor": "Supervisor",
    "platform_admin": "Platform",
}
ROLE_WORKSPACES = {
    "candidate": "candidate",
    "employee": "staff",
    "supervisor": "staff",
    "platform_admin": "platform",
}
ROLE_DESCRIPTIONS = {
    "candidate": "A place for your profile, opportunities, and application updates.",
    "employee": "A shared staff workspace for candidate and application work.",
    "supervisor": "The staff workspace from a team and assignment perspective.",
    "platform_admin": "A foundation for the future platform administration experience.",
}


@dataclass
class AuthContext:
    user: User
    session: AuthSession
    agency: Agency | None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def active_memberships(db: DbSession, user_id: str) -> list[Membership]:
    return list(
        db.scalars(
            select(Membership)
            .where(Membership.user_id == user_id, Membership.active.is_(True))
            .order_by(Membership.created_at)
        )
    )


def create_session(
    db: DbSession, user: User, active_agency_id: str | None
) -> tuple[AuthSession, str, str]:
    settings = get_settings()
    token = new_secret()
    csrf = new_secret()
    record = AuthSession(
        user_id=user.id,
        token_hash=hash_secret(token),
        csrf_hash=hash_secret(csrf),
        active_agency_id=active_agency_id,
        expires_at=utcnow() + timedelta(days=settings.session_days),
    )
    db.add(record)
    db.flush()
    return record, token, csrf


def _membership_for_agency(db: DbSession, user_id: str, agency_id: str) -> Membership | None:
    return db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.agency_id == agency_id,
            Membership.active.is_(True),
        )
    )


def resolve_session(db: DbSession, token: str | None) -> AuthContext | None:
    if not token:
        return None
    record = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_secret(token)))
    if not record or record.revoked_at is not None or record.expires_at <= utcnow():
        return None
    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        return None
    agency = db.get(Agency, record.active_agency_id) if record.active_agency_id else None

    if user.role == "platform_admin":
        return AuthContext(user=user, session=record, agency=None)

    if user.role == "candidate":
        # Independent candidates have no agency. Referred candidates carry an agency
        # context and must still hold an active membership in it.
        if agency is None:
            return AuthContext(user=user, session=record, agency=None)
        if agency.status != "active" or not _membership_for_agency(db, user.id, agency.id):
            return None
        return AuthContext(user=user, session=record, agency=agency)

    if not agency or agency.status != "active":
        return None
    if not _membership_for_agency(db, user.id, agency.id):
        return None
    return AuthContext(user=user, session=record, agency=agency)


def verify_csrf(record: AuthSession, token: str) -> bool:
    import secrets

    return secrets.compare_digest(record.csrf_hash, hash_secret(token))


def session_out(db: DbSession, context: AuthContext) -> SessionOut:
    agencies = [
        AgencyOut(id=membership.agency.id, name=membership.agency.name)
        for membership in active_memberships(db, context.user.id)
        if membership.agency is not None
    ]
    user = SessionUserOut(
        id=context.user.id,
        name=context.user.name,
        email=context.user.email,
        role=context.user.role,
        label=ROLE_LABELS[context.user.role],
        workspace=ROLE_WORKSPACES[context.user.role],
        agencies=agencies,
    )
    agency = AgencyOut(id=context.agency.id, name=context.agency.name) if context.agency else None
    return SessionOut(user=user, agency=agency)


def _resolve_login_agency(
    db: DbSession, user: User, requested_agency_id: str | None
) -> Agency | None:
    if user.role == "platform_admin":
        return None
    memberships = active_memberships(db, user.id)
    if user.role == "candidate" and not memberships and not requested_agency_id:
        return None
    if not memberships:
        raise Forbidden("This account has no active agency membership.")
    if requested_agency_id:
        membership = next(
            (item for item in memberships if item.agency_id == requested_agency_id), None
        )
        if not membership:
            raise Forbidden("That agency is not part of this account.")
        return membership.agency
    return memberships[0].agency


def login(
    db: DbSession, email: str, password: str, agency_id: str | None = None
) -> tuple[AuthContext, str, str]:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if not user or not verify_password(password, user.password_hash):
        raise Unauthorized("Email or password is incorrect.")
    if not user.is_active:
        raise Unauthorized("This account is not active.")
    agency = _resolve_login_agency(db, user, agency_id)
    record, token, csrf = create_session(db, user, agency.id if agency else None)
    db.commit()
    db.refresh(record)
    return AuthContext(user=user, session=record, agency=agency), token, csrf


def register(
    db: DbSession,
    name: str,
    email: str,
    password: str,
    referral_token: str | None = None,
) -> tuple[AuthContext, str, str]:
    normalized = normalize_email(email)
    if db.scalar(select(User).where(User.email == normalized)):
        raise Conflict("An account with that email already exists.")

    resolved = referrals_service.resolve(db, referral_token) if referral_token else None
    if resolved is not None and not resolved.valid:
        raise Conflict(resolved.reason or "This referral link is not valid.")

    user = User(
        email=normalized,
        name=name.strip(),
        password_hash=hash_password(password),
        role="candidate",
    )
    db.add(user)
    db.flush()

    agency: Agency | None = None
    if referral_token:
        link = referrals_service.consume(db, referral_token, user.id)
        agency = link.agency
        if not agency or agency.status != "active":
            raise Conflict("That agency is not currently accepting referrals.")
        db.add(Membership(user_id=user.id, agency_id=agency.id, title="Candidate"))
        candidates_service.bootstrap_candidate(db, user, agency.id)
        db.add(
            CandidateAssignment(
                agency_id=agency.id,
                candidate_id=user.id,
                member_id=link.created_by,
            )
        )
    else:
        candidates_service.bootstrap_candidate(db, user, None)

    record, token, csrf = create_session(db, user, agency.id if agency else None)
    db.commit()
    return AuthContext(user=user, session=record, agency=agency), token, csrf


def demo_personas(db: DbSession) -> list[DemoPersonaOut]:
    users = list(db.scalars(select(User).where(User.is_demo.is_(True)).order_by(User.created_at)))
    return [
        DemoPersonaOut(
            id=user.id,
            name=user.name,
            role=user.role,
            label=ROLE_LABELS[user.role],
            description=ROLE_DESCRIPTIONS[user.role],
            workspace=ROLE_WORKSPACES[user.role],
        )
        for user in users
    ]


def demo_login(db: DbSession, persona_id: str) -> tuple[AuthContext, str, str]:
    if not get_settings().demo_login_enabled:
        raise NotFound("Demo sign-in is not enabled.")
    user = db.get(User, persona_id)
    if not user or not user.is_demo or not user.is_active:
        raise NotFound("That demo perspective is not available.")
    agency = _resolve_login_agency(db, user, None)
    record, token, csrf = create_session(db, user, agency.id if agency else None)
    db.commit()
    return AuthContext(user=user, session=record, agency=agency), token, csrf


def logout(db: DbSession, context: AuthContext) -> None:
    context.session.revoked_at = utcnow()
    db.commit()


def switch_agency(db: DbSession, context: AuthContext, agency_id: str) -> AuthContext:
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == context.user.id,
            Membership.agency_id == agency_id,
            Membership.active.is_(True),
        )
    )
    if not membership:
        raise Forbidden("That agency is not part of this account.")
    agency = db.get(Agency, agency_id)
    if not agency or agency.status != "active":
        raise Forbidden("That agency is not active.")
    context.session.active_agency_id = agency.id
    db.commit()
    return AuthContext(user=context.user, session=context.session, agency=agency)


def change_password(
    db: DbSession, context: AuthContext, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, context.user.password_hash):
        raise Unauthorized("Your current password is incorrect.")
    context.user.password_hash = hash_password(new_password)
    for record in db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == context.user.id,
            AuthSession.revoked_at.is_(None),
        )
    ):
        record.revoked_at = utcnow()
    db.commit()
