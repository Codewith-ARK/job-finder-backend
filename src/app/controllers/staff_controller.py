from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..schemas.staff_schema import (
    AssignmentInput,
    MemberCreatedOut,
    MemberCreateInput,
    MemberPatch,
    StaffWorkspaceOut,
    StageInput,
)
from ..security import current_staff, require_agency, require_supervisor
from ..services import staff_service

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/workspace", response_model=StaffWorkspaceOut)
def read_workspace(
    context=Depends(current_staff), db: DbSession = Depends(get_db)
) -> StaffWorkspaceOut:
    agency = require_agency(context)
    return staff_service.workspace(db, agency.id)


@router.post("/candidates/{candidate_id}/assignment", response_model=StaffWorkspaceOut)
def assign_candidate(
    candidate_id: str,
    payload: AssignmentInput,
    context=Depends(require_supervisor),
    db: DbSession = Depends(get_db),
) -> StaffWorkspaceOut:
    agency = require_agency(context)
    return staff_service.assign_candidate(
        db, agency.id, context.user, candidate_id, payload.member_id
    )


@router.patch("/candidates/{candidate_id}/stage", response_model=StaffWorkspaceOut)
def update_stage(
    candidate_id: str,
    payload: StageInput,
    context=Depends(require_supervisor),
    db: DbSession = Depends(get_db),
) -> StaffWorkspaceOut:
    agency = require_agency(context)
    return staff_service.update_stage(db, agency.id, context.user, candidate_id, payload.stage)


@router.post("/members", response_model=MemberCreatedOut)
def create_member(
    payload: MemberCreateInput,
    context=Depends(require_supervisor),
    db: DbSession = Depends(get_db),
) -> MemberCreatedOut:
    agency = require_agency(context)
    return staff_service.create_member(db, agency.id, context.user, payload)


@router.patch("/members/{member_id}", response_model=StaffWorkspaceOut)
def update_member(
    member_id: str,
    payload: MemberPatch,
    context=Depends(require_supervisor),
    db: DbSession = Depends(get_db),
) -> StaffWorkspaceOut:
    agency = require_agency(context)
    return staff_service.update_member(db, agency.id, context.user, member_id, payload)
