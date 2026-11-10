from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..schemas.jobs_schema import (
    ApplicationStatusInput,
    JobInput,
    JobPatch,
    JobsWorkspaceOut,
)
from ..security import (
    current_agency_user,
    require_agency,
    require_candidate,
    require_staff,
    require_supervisor,
)
from ..services import jobs_service

router = APIRouter(tags=["jobs"])


@router.get("/jobs/workspace", response_model=JobsWorkspaceOut)
def read_workspace(
    context=Depends(current_agency_user), db: DbSession = Depends(get_db)
) -> JobsWorkspaceOut:
    agency = require_agency(context)
    return jobs_service.workspace(db, agency.id, context.user)


@router.post("/jobs", response_model=JobsWorkspaceOut)
def create_job(
    payload: JobInput,
    context=Depends(require_supervisor),
    db: DbSession = Depends(get_db),
) -> JobsWorkspaceOut:
    agency = require_agency(context)
    return jobs_service.create_job(db, agency.id, context.user, payload)


@router.patch("/jobs/{job_id}", response_model=JobsWorkspaceOut)
def update_job(
    job_id: str,
    payload: JobPatch,
    context=Depends(require_supervisor),
    db: DbSession = Depends(get_db),
) -> JobsWorkspaceOut:
    agency = require_agency(context)
    return jobs_service.update_job(db, agency.id, context.user, job_id, payload)


@router.post("/jobs/{job_id}/apply", response_model=JobsWorkspaceOut)
def apply_to_job(
    job_id: str,
    context=Depends(require_candidate),
    db: DbSession = Depends(get_db),
) -> JobsWorkspaceOut:
    agency = require_agency(context)
    return jobs_service.apply_to_job(db, agency.id, context.user, job_id)


@router.patch("/applications/{application_id}", response_model=JobsWorkspaceOut)
def update_application(
    application_id: str,
    payload: ApplicationStatusInput,
    context=Depends(require_staff),
    db: DbSession = Depends(get_db),
) -> JobsWorkspaceOut:
    agency = require_agency(context)
    return jobs_service.update_application(db, agency.id, context.user, application_id, payload)
