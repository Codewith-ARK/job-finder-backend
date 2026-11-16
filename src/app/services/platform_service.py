from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ..config import get_settings
from ..models import Agency, AuditEvent, Integration, Membership, User
from ..schemas.platform_schema import (
    AgencyStatusInput,
    AuditOut,
    IntegrationOut,
    PlatformAgencyOut,
    PlatformStatsOut,
    PlatformWorkspaceOut,
)
from .errors import NotFound


def workspace(db: DbSession) -> PlatformWorkspaceOut:
    limit = get_settings().max_workspace_items
    agencies = list(db.scalars(select(Agency).order_by(Agency.name).limit(limit)))
    integrations = list(
        db.scalars(select(Integration).order_by(Integration.name).limit(limit))
    )
    connected = sum(1 for item in integrations if item.status == "connected")
    counts = dict(
        db.execute(
            select(Membership.agency_id, func.count(Membership.id))
            .where(Membership.active.is_(True))
            .group_by(Membership.agency_id)
        ).all()
    )
    agencies_out = []
    for agency in agencies:
        users = counts.get(agency.id, 0)
        agencies_out.append(
            PlatformAgencyOut(
                id=agency.id,
                name=agency.name,
                region=agency.region or "—",
                users=int(users or 0),
                status=agency.status,
                integrations=f"{connected} / {len(integrations)}",
            )
        )
    audit = list(db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(30)))
    actor_ids = {item.actor_id for item in audit if item.actor_id}
    actors = (
        {user.id: user.name for user in db.scalars(select(User).where(User.id.in_(actor_ids)))}
        if actor_ids
        else {}
    )
    return PlatformWorkspaceOut(
        stats=PlatformStatsOut(
            agencies=len(agencies),
            users=int(db.scalar(select(func.count(User.id))) or 0),
            integrations=len(integrations),
            health="Degraded"
            if any(item.status == "error" for item in integrations)
            else "Healthy",
        ),
        agencies=agencies_out,
        integrations=[
            IntegrationOut(
                id=item.id,
                name=item.name,
                type=item.type,
                status=item.status,
                last_sync=item.last_sync,
            )
            for item in integrations
        ],
        audit=[
            AuditOut(
                id=item.id,
                event=item.event,
                detail=item.detail,
                actor=actors.get(item.actor_id or "", "System"),
                created_at=item.created_at,
            )
            for item in audit
        ],
    )


def update_agency_status(
    db: DbSession, actor: User, agency_id: str, payload: AgencyStatusInput
) -> PlatformWorkspaceOut:
    agency = db.get(Agency, agency_id)
    if not agency:
        raise NotFound("That agency was not found.")
    agency.status = payload.status
    db.add(
        AuditEvent(
            actor_id=actor.id,
            agency_id=agency.id,
            event="Agency status updated",
            detail=f"{agency.name} set to {payload.status}",
        )
    )
    db.commit()
    return workspace(db)
