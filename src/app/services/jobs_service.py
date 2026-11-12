from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..models import Activity, Agency, Application, Job, User
from ..models.common import utcnow
from ..schemas.jobs_schema import (
    ApplicationOut,
    ApplicationStatusInput,
    JobInput,
    JobOut,
    JobPatch,
    JobsWorkspaceOut,
)
from . import candidates_service
from .errors import Conflict, NotFound
from .text import MAX_ACTIVITY_DETAIL, MAX_ACTIVITY_TITLE, clip

NEXT_STEPS = {
    "submitted": "The team will review your application",
    "review": "Usually responds in 1–2 weeks",
    "interview": "Interview scheduled",
    "offer": "Review your offer",
    "closed": "Application closed",
}


def _job_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        agency_name=job.agency.name if job.agency else "",
        title=job.title,
        company=job.company,
        location=job.location,
        work_type=job.work_type,
        salary=job.salary,
        tags=job.tags or [],
        status=job.status,
        posted=job.created_at,
        description=job.description,
    )


def _application_out(application: Application) -> ApplicationOut:
    return ApplicationOut(
        id=application.id,
        job_id=application.job_id,
        job_title=application.job.title if application.job else "Role unavailable",
        company=application.job.company if application.job else "",
        agency_name=(
            application.job.agency.name if application.job and application.job.agency else ""
        ),
        candidate_id=application.candidate_id,
        candidate_name=application.candidate.name if application.candidate else "Candidate",
        status=application.status,
        submitted_at=application.created_at,
        next_step=application.next_step or NEXT_STEPS.get(application.status, ""),
        updated_at=application.updated_at,
    )


def workspace(db: DbSession, agency_id: str | None, user: User) -> JobsWorkspaceOut:
    limit = get_settings().max_workspace_items
    if user.role == "candidate" and agency_id is None:
        # Independent candidates browse every open role from active agencies.
        job_query = (
            select(Job)
            .join(Agency, Agency.id == Job.agency_id)
            .options(selectinload(Job.agency))
            .where(Job.status == "open", Agency.status == "active")
        )
    else:
        job_query = (
            select(Job)
            .options(selectinload(Job.agency))
            .where(Job.agency_id == agency_id)
        )
        if user.role == "candidate":
            job_query = job_query.where(Job.status == "open")
    jobs = list(db.scalars(job_query.order_by(Job.created_at.desc()).limit(limit)))
    application_query = (
        select(Application)
        .options(
            selectinload(Application.candidate),
            selectinload(Application.job).selectinload(Job.agency),
        )
    )
    if user.role == "candidate":
        application_query = application_query.where(Application.candidate_id == user.id)
    else:
        application_query = application_query.where(Application.agency_id == agency_id)
    applications = list(
        db.scalars(application_query.order_by(Application.updated_at.desc()).limit(limit))
    )
    return JobsWorkspaceOut(
        jobs=[_job_out(job) for job in jobs],
        applications=[_application_out(item) for item in applications],
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


def create_job(db: DbSession, agency_id: str, actor: User, payload: JobInput) -> JobsWorkspaceOut:
    job = Job(
        agency_id=agency_id,
        title=payload.title.strip(),
        company=payload.company.strip(),
        location=payload.location.strip(),
        work_type=payload.work_type,
        salary=payload.salary.strip(),
        tags=[tag.strip() for tag in payload.tags if tag.strip()],
        description=payload.description.strip(),
        created_by=actor.id,
    )
    db.add(job)
    _log(
        db, agency_id, actor.id, f"{job.title} published", "New role added to the board", "success"
    )
    db.commit()
    return workspace(db, agency_id, actor)


def _job_in_agency(db: DbSession, agency_id: str, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job or job.agency_id != agency_id:
        raise NotFound("That job is no longer available.")
    return job


def update_job(
    db: DbSession, agency_id: str, actor: User, job_id: str, payload: JobPatch
) -> JobsWorkspaceOut:
    job = _job_in_agency(db, agency_id, job_id)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        if field == "tags":
            value = [tag.strip() for tag in value if tag.strip()]
        if isinstance(value, str):
            value = value.strip()
        setattr(job, field, value)
    _log(db, agency_id, actor.id, f"{job.title} updated", "Role details changed", "info")
    db.commit()
    return workspace(db, agency_id, actor)


def apply_to_job(
    db: DbSession, candidate: User, job_id: str, agency_id: str | None
) -> JobsWorkspaceOut:
    job = db.get(Job, job_id)
    if job and agency_id is not None and job.agency_id != agency_id:
        raise NotFound("That job is no longer available.")
    if not job or job.status != "open":
        raise Conflict("That role is no longer accepting applications.")
    if not job.agency or job.agency.status != "active":
        raise Conflict("That agency is not currently accepting applications.")
    if not candidates_service.onboarding_complete(db, candidate.id):
        raise Conflict("Complete your onboarding before applying to roles.")
    existing = db.scalar(
        select(Application).where(
            Application.job_id == job.id,
            Application.candidate_id == candidate.id,
        )
    )
    if existing:
        raise Conflict("You have already applied to this role.")
    db.add(
        Application(
            agency_id=job.agency_id,
            job_id=job.id,
            candidate_id=candidate.id,
            status="submitted",
            next_step=NEXT_STEPS["submitted"],
        )
    )
    _log(
        db,
        job.agency_id,
        candidate.id,
        f"{candidate.name} applied to {job.title}",
        job.company,
        "success",
    )
    db.commit()
    return workspace(db, agency_id, candidate)


def update_application(
    db: DbSession,
    agency_id: str,
    actor: User,
    application_id: str,
    payload: ApplicationStatusInput,
) -> JobsWorkspaceOut:
    application = db.get(Application, application_id)
    if not application or application.agency_id != agency_id:
        raise NotFound("That application is no longer available.")
    application.status = payload.status
    application.next_step = NEXT_STEPS[payload.status]
    application.updated_at = utcnow()
    candidate = db.get(User, application.candidate_id)
    job = db.get(Job, application.job_id)
    _log(
        db,
        agency_id,
        actor.id,
        f"{candidate.name if candidate else 'Candidate'}'s application moved to {payload.status}",
        f"{job.title if job else 'Role'} · updated by {actor.name}",
        "success" if payload.status in ("offer", "interview") else "info",
    )
    db.commit()
    return workspace(db, agency_id, actor)
