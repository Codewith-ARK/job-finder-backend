import secrets
from collections import Counter
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..models import (
    Activity,
    Agency,
    Application,
    AuthSession,
    CandidateAssignment,
    CandidateProfile,
    Membership,
    Team,
    User,
)
from ..models.common import utcnow
from ..schemas.staff_schema import (
    ActivityOut,
    MemberCreatedOut,
    MemberCreateInput,
    MemberPatch,
    StaffCandidateOut,
    StaffStatsOut,
    StaffWorkspaceOut,
    TeamMemberOut,
)
from . import candidates_service
from .credentials import hash_password
from .errors import Conflict, Forbidden, NotFound
from .text import MAX_ACTIVITY_DETAIL, MAX_ACTIVITY_TITLE, clip

STEP_WEIGHTS = candidates_service.STEP_WEIGHTS


def _agency(db: DbSession, agency_id: str) -> Agency:
    agency = db.get(Agency, agency_id)
    if not agency:
        raise NotFound("That agency was not found.")
    return agency


def _candidate_profiles(db: DbSession, agency_id: str) -> list[CandidateProfile]:
    return list(
        db.scalars(
            select(CandidateProfile)
            .join(User, User.id == CandidateProfile.user_id)
            .join(Membership, Membership.user_id == CandidateProfile.user_id)
            .options(
                selectinload(CandidateProfile.steps),
                selectinload(CandidateProfile.user),
                selectinload(CandidateProfile.skills),
            )
            .where(
                Membership.agency_id == agency_id,
                Membership.active.is_(True),
                User.is_active.is_(True),
                User.role == "candidate",
            )
            .order_by(CandidateProfile.updated_at.desc())
            .limit(get_settings().max_workspace_items)
        )
    )


def _completion(profile: CandidateProfile) -> int:
    return min(
        100,
        sum(STEP_WEIGHTS.get(step.key, 0) for step in profile.steps if step.status == "complete"),
    )


def _assignments(db: DbSession, agency_id: str) -> dict[str, CandidateAssignment]:
    rows = db.scalars(
        select(CandidateAssignment)
        .where(CandidateAssignment.agency_id == agency_id)
        .limit(get_settings().max_workspace_items)
    )
    return {row.candidate_id: row for row in rows}


def _staff_memberships(db: DbSession, agency_id: str) -> list[Membership]:
    return list(
        db.scalars(
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .options(selectinload(Membership.user), selectinload(Membership.team))
            .where(
                Membership.agency_id == agency_id,
                User.role.in_(("employee", "supervisor")),
            )
            .order_by(Membership.created_at)
            .limit(get_settings().max_workspace_items)
        )
    )


def workspace(db: DbSession, agency_id: str) -> StaffWorkspaceOut:
    profiles = _candidate_profiles(db, agency_id)
    assignments = _assignments(db, agency_id)
    workloads = Counter(row.member_id for row in assignments.values())
    memberships = _staff_memberships(db, agency_id)
    teams = [
        team.name
        for team in db.scalars(
            select(Team)
            .where(Team.agency_id == agency_id)
            .order_by(Team.name)
            .limit(get_settings().max_workspace_items)
        )
    ]
    activity = list(
        db.scalars(
            select(Activity)
            .where(Activity.agency_id == agency_id)
            .order_by(Activity.created_at.desc())
            .limit(20)
        )
    )
    application_activity = db.scalar(
        select(func.count(Application.id)).where(
            Application.agency_id == agency_id,
            Application.updated_at >= utcnow() - timedelta(days=7),
        )
    )
    candidates = [
        StaffCandidateOut(
            id=profile.user_id,
            name=profile.user.name,
            headline=profile.headline or "Candidate",
            location=profile.location or "Not set",
            status=profile.stage,
            onboarding=_completion(profile),
            assigned_to=assignments[profile.user_id].member_id
            if profile.user_id in assignments
            else None,
            skills=[skill.name for skill in profile.skills],
            updated_at=profile.updated_at,
        )
        for profile in profiles
    ]
    return StaffWorkspaceOut(
        stats=StaffStatsOut(
            active_candidates=len(candidates),
            open_assignments=len(assignments),
            onboarding_in_progress=sum(1 for profile in profiles if profile.stage == "onboarding"),
            application_activity=int(application_activity or 0),
        ),
        candidates=candidates,
        team_members=[
            TeamMemberOut(
                id=membership.user_id,
                name=membership.user.name,
                email=membership.user.email,
                role=membership.user.role,
                team=membership.team.name if membership.team else "Unassigned",
                workload=min(100, workloads[membership.user_id] * 25),
                active=membership.active and membership.user.is_active,
            )
            for membership in memberships
        ],
        teams=teams,
        activity=[
            ActivityOut(
                id=item.id,
                title=item.title,
                detail=item.detail,
                tone=item.tone,
                created_at=item.created_at,
            )
            for item in activity
        ],
    )


def _log(
    db: DbSession,
    agency_id: str,
    actor_id: str | None,
    title: str,
    detail: str,
    tone: str = "info",
) -> None:
    db.add(
        Activity(
            agency_id=agency_id,
            actor_id=actor_id,
            title=clip(title, MAX_ACTIVITY_TITLE),
            detail=clip(detail, MAX_ACTIVITY_DETAIL),
            tone=tone,
        )
    )


def _member_in_agency(db: DbSession, agency_id: str, member_id: str) -> Membership:
    membership = db.scalar(
        select(Membership)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.agency_id == agency_id,
            Membership.user_id == member_id,
            Membership.active.is_(True),
            User.is_active.is_(True),
        )
    )
    if not membership or membership.user.role not in ("employee", "supervisor"):
        raise NotFound("Choose an active team member in this agency.")
    return membership


def assign_candidate(
    db: DbSession,
    agency_id: str,
    actor: User,
    candidate_id: str,
    member_id: str | None,
) -> StaffWorkspaceOut:
    profile = db.get(CandidateProfile, candidate_id)
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == candidate_id,
            Membership.agency_id == agency_id,
            Membership.active.is_(True),
        )
    )
    if not profile or not membership:
        raise NotFound("That candidate is not available in this agency.")
    assignment = db.scalar(
        select(CandidateAssignment).where(
            CandidateAssignment.agency_id == agency_id,
            CandidateAssignment.candidate_id == candidate_id,
        )
    )
    candidate = db.get(User, candidate_id)
    if member_id is None:
        if assignment:
            db.delete(assignment)
            _log(
                db,
                agency_id,
                actor.id,
                f"{candidate.name if candidate else 'Candidate'} unassigned",
                "Assignment removed",
                "warning",
            )
    else:
        membership = _member_in_agency(db, agency_id, member_id)
        if assignment:
            assignment.member_id = member_id
        else:
            db.add(
                CandidateAssignment(
                    agency_id=agency_id,
                    candidate_id=candidate_id,
                    member_id=member_id,
                )
            )
        if profile.stage == "onboarding":
            profile.stage = "review"
        profile.updated_at = utcnow()
        _log(
            db,
            agency_id,
            actor.id,
            f"{candidate.name if candidate else 'Candidate'} assigned to {membership.user.name}",
            "Assignment updated successfully",
            "success",
        )
    db.commit()
    return workspace(db, agency_id)


def update_stage(
    db: DbSession, agency_id: str, actor: User, candidate_id: str, stage: str
) -> StaffWorkspaceOut:
    profile = db.get(CandidateProfile, candidate_id)
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == candidate_id,
            Membership.agency_id == agency_id,
            Membership.active.is_(True),
        )
    )
    if not profile or not membership:
        raise NotFound("That candidate is not available in this agency.")
    profile.stage = stage
    profile.updated_at = utcnow()
    candidate = db.get(User, candidate_id)
    _log(
        db,
        agency_id,
        actor.id,
        f"{candidate.name if candidate else 'Candidate'} moved to {stage}",
        "Pipeline stage updated",
        "info",
    )
    db.commit()
    return workspace(db, agency_id)


def _team(db: DbSession, agency_id: str, name: str) -> Team:
    team = db.scalar(select(Team).where(Team.agency_id == agency_id, Team.name == name.strip()))
    if team:
        return team
    team = Team(agency_id=agency_id, name=name.strip())
    db.add(team)
    db.flush()
    return team


def create_member(
    db: DbSession, agency_id: str, actor: User, payload: MemberCreateInput
) -> MemberCreatedOut:
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise Conflict("An account with that email already exists.")
    temporary_password = secrets.token_urlsafe(9)
    user = User(
        email=email,
        name=payload.name.strip(),
        password_hash=hash_password(temporary_password),
        role=payload.role,
    )
    db.add(user)
    db.flush()
    team = _team(db, agency_id, payload.team)
    db.add(
        Membership(
            user_id=user.id,
            agency_id=agency_id,
            title="Team member",
            team_id=team.id,
        )
    )
    _log(
        db,
        agency_id,
        actor.id,
        f"{user.name} added to the team",
        f"{team.name} · share the temporary password securely",
        "info",
    )
    db.commit()
    return MemberCreatedOut(
        workspace=workspace(db, agency_id), temporary_password=temporary_password
    )


def update_member(
    db: DbSession,
    agency_id: str,
    actor: User,
    member_id: str,
    payload: MemberPatch,
) -> StaffWorkspaceOut:
    membership = db.scalar(
        select(Membership).where(
            Membership.agency_id == agency_id,
            Membership.user_id == member_id,
        )
    )
    if not membership:
        raise NotFound("That team member is not part of this agency.")
    member = membership.user
    if actor.id == member.id and payload.active is False:
        raise Forbidden("You cannot deactivate your own account.")
    if member.role not in ("employee", "supervisor"):
        raise Forbidden("Only agency staff can be managed here.")

    changing_role = payload.role is not None and payload.role != member.role
    demoting_supervisor = (
        changing_role and member.role == "supervisor" and payload.role != "supervisor"
    )
    deactivating = payload.active is False and membership.active

    if changing_role:
        # Roles are global, so a tenant supervisor must not change authority that
        # also applies in another agency. Platform administration owns that change.
        other_membership = db.scalar(
            select(func.count(Membership.id)).where(
                Membership.user_id == member.id,
                Membership.agency_id != agency_id,
                Membership.active.is_(True),
            )
        )
        if other_membership:
            raise Forbidden(
                "Role changes for members of multiple agencies require platform administration."
            )

    if (demoting_supervisor or (deactivating and member.role == "supervisor")):
        remaining_supervisors = db.scalar(
            select(func.count(Membership.id))
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.agency_id == agency_id,
                Membership.user_id != member.id,
                Membership.active.is_(True),
                User.is_active.is_(True),
                User.role == "supervisor",
            )
        )
        if not remaining_supervisors:
            raise Conflict("An agency must keep at least one active supervisor.")

    if payload.role is not None:
        member.role = payload.role
    if payload.team is not None:
        membership.team_id = _team(db, agency_id, payload.team).id
    if payload.active is not None:
        membership.active = payload.active
        if payload.active:
            member.is_active = True
        else:
            # Only revoke this agency's access; other memberships stay intact.
            for record in db.scalars(
                select(AuthSession).where(
                    AuthSession.user_id == member.id,
                    AuthSession.active_agency_id == agency_id,
                    AuthSession.revoked_at.is_(None),
                )
            ):
                record.revoked_at = utcnow()
            db.flush()
            remaining = db.scalar(
                select(func.count(Membership.id)).where(
                    Membership.user_id == member.id,
                    Membership.active.is_(True),
                )
            )
            if not remaining:
                member.is_active = False
    _log(
        db,
        agency_id,
        actor.id,
        f"{member.name} updated",
        "Team membership updated",
        "info",
    )
    db.commit()
    return workspace(db, agency_id)
