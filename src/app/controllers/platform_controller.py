from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..schemas.platform_schema import (
    AgencyStatusInput,
    PlatformWorkspaceOut,
)
from ..security import current_platform_admin, require_platform_admin
from ..services import platform_service

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/workspace", response_model=PlatformWorkspaceOut)
def read_workspace(
    _context=Depends(current_platform_admin), db: DbSession = Depends(get_db)
) -> PlatformWorkspaceOut:
    return platform_service.workspace(db)


@router.patch("/agencies/{agency_id}", response_model=PlatformWorkspaceOut)
def update_agency_status(
    agency_id: str,
    payload: AgencyStatusInput,
    context=Depends(require_platform_admin),
    db: DbSession = Depends(get_db),
) -> PlatformWorkspaceOut:
    return platform_service.update_agency_status(db, context.user, agency_id, payload)
