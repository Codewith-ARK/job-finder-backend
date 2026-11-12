from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DbSession

from ..config import get_settings
from ..database import get_db
from ..schemas.candidates_schema import (
    AcademicStepInput,
    CandidateWorkspaceOut,
    PersonalStepInput,
    ProfessionalStepInput,
)
from ..security import current_candidate, require_candidate
from ..services import candidates_service
from ..services.errors import NotFound

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/me", response_model=CandidateWorkspaceOut)
def read_workspace(
    context=Depends(current_candidate), db: DbSession = Depends(get_db)
) -> CandidateWorkspaceOut:
    return candidates_service.workspace(db, context.user)


@router.put("/me/onboarding/personal", response_model=CandidateWorkspaceOut)
def save_personal(
    payload: PersonalStepInput,
    context=Depends(require_candidate),
    db: DbSession = Depends(get_db),
) -> CandidateWorkspaceOut:
    return candidates_service.save_personal(db, context.user, payload)


@router.put("/me/onboarding/professional", response_model=CandidateWorkspaceOut)
def save_professional(
    payload: ProfessionalStepInput,
    context=Depends(require_candidate),
    db: DbSession = Depends(get_db),
) -> CandidateWorkspaceOut:
    return candidates_service.save_professional(db, context.user, payload)


@router.put("/me/onboarding/academic", response_model=CandidateWorkspaceOut)
def save_academic(
    payload: AcademicStepInput,
    context=Depends(require_candidate),
    db: DbSession = Depends(get_db),
) -> CandidateWorkspaceOut:
    return candidates_service.save_academic(db, context.user, payload)


@router.post("/me/onboarding/{step_id}/complete", response_model=CandidateWorkspaceOut)
def complete_step(
    step_id: str,
    context=Depends(require_candidate),
    db: DbSession = Depends(get_db),
) -> CandidateWorkspaceOut:
    return candidates_service.complete_step(db, context.user, step_id)


@router.post("/me/documents", response_model=CandidateWorkspaceOut)
async def upload_document(
    file: UploadFile = File(...),
    context=Depends(require_candidate),
    db: DbSession = Depends(get_db),
) -> CandidateWorkspaceOut:
    content = await file.read(get_settings().max_upload_bytes + 1)
    return candidates_service.add_document(
        db,
        context.user,
        file.filename or "document",
        file.content_type or "",
        content,
    )


@router.get("/me/documents/{document_id}")
def download_document(
    document_id: str,
    context=Depends(current_candidate),
    db: DbSession = Depends(get_db),
) -> FileResponse:
    document = candidates_service.get_document(db, context.user, document_id)
    path = Path(document.storage_path)
    if not path.exists():
        raise NotFound("The stored document could not be found.")
    return FileResponse(path, filename=document.filename, media_type=document.content_type)


@router.delete("/me/documents/{document_id}", response_model=CandidateWorkspaceOut)
def remove_document(
    document_id: str,
    context=Depends(require_candidate),
    db: DbSession = Depends(get_db),
) -> CandidateWorkspaceOut:
    return candidates_service.delete_document(db, context.user, document_id)
