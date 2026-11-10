from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ..config import get_settings
from ..models import (
    Activity,
    CandidateProfile,
    Document,
    Membership,
    User,
)
from ..models.common import utcnow
from ..schemas.candidates_schema import (
    CandidateWorkspaceOut,
    DocumentOut,
    OnboardingStepOut,
    PreferencesPatch,
    ProfileOut,
    ProfilePatch,
)
from .auth_service import ONBOARDING
from .errors import Conflict, Forbidden, NotFound

STEP_WEIGHTS = {"profile": 40, "preferences": 30, "documents": 30}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_SKILLS = 30


def _profile(db: DbSession, user_id: str) -> CandidateProfile:
    profile = db.get(CandidateProfile, user_id)
    if not profile:
        raise NotFound("A candidate profile has not been created for this account.")
    return profile


def _completion(profile: CandidateProfile) -> int:
    return min(
        100,
        sum(STEP_WEIGHTS.get(step.key, 0) for step in profile.steps if step.status == "complete"),
    )


def _step_statuses(profile: CandidateProfile) -> list[OnboardingStepOut]:
    descriptions = {key: description for key, _title, description in ONBOARDING}
    titles = {key: title for key, title, _description in ONBOARDING}
    return [
        OnboardingStepOut(
            id=step.key,
            title=titles[step.key],
            description=descriptions[step.key],
            status=step.status,
        )
        for step in profile.steps
    ]


def _next_steps(profile: CandidateProfile) -> list[str]:
    next_step = next((step for step in profile.steps if step.status == "next"), None)
    if not next_step:
        return [
            "Browse open roles in your workspace.",
            "Apply to a role that fits your goals.",
            "Track every update from your team here.",
        ]
    return {
        "profile": [
            "Finish the profile details your team can review.",
            "Share the kind of roles and work environment you prefer.",
            "Upload your CV so your team can prepare.",
        ],
        "preferences": [
            "Tell your team what kind of work feels right.",
            "Add your CV and supporting documents.",
            "Browse roles matched to your preferences.",
        ],
        "documents": [
            "Upload your CV and any supporting files.",
            "Check that your profile is current.",
            "Apply to a role that fits your goals.",
        ],
    }[next_step.key]


def workspace(db: DbSession, user: User) -> CandidateWorkspaceOut:
    profile = _profile(db, user.id)
    documents = sorted(profile.documents, key=lambda item: item.created_at, reverse=True)
    return CandidateWorkspaceOut(
        profile=ProfileOut(
            name=user.name,
            email=user.email,
            headline=profile.headline,
            location=profile.location,
            skills=profile.skills or [],
            completion=_completion(profile),
            preferred_work_type=profile.preferred_work_type,
            preferred_location=profile.preferred_location,
            salary_expectation=profile.salary_expectation,
        ),
        onboarding=_step_statuses(profile),
        next_steps=_next_steps(profile),
        documents=[
            DocumentOut(
                id=document.id,
                filename=document.filename,
                size=document.size,
                created_at=document.created_at,
            )
            for document in documents
        ],
    )


def _advance_steps(profile: CandidateProfile) -> None:
    next_assigned = False
    for step in profile.steps:
        if step.status == "complete":
            continue
        step.status = "upcoming" if next_assigned else "next"
        next_assigned = True


def _log(db: DbSession, agency_id: str, user_id: str, title: str, detail: str) -> None:
    db.add(
        Activity(
            agency_id=agency_id,
            actor_id=user_id,
            title=title,
            detail=detail,
            tone="info",
        )
    )


def update_profile(db: DbSession, user: User, patch: ProfilePatch) -> CandidateWorkspaceOut:
    profile = _profile(db, user.id)
    profile.headline = patch.headline.strip()
    profile.location = patch.location.strip()
    profile.skills = [skill.strip() for skill in patch.skills if skill.strip()][:MAX_SKILLS]
    profile.updated_at = utcnow()
    db.commit()
    return workspace(db, user)


def update_preferences(db: DbSession, user: User, patch: PreferencesPatch) -> CandidateWorkspaceOut:
    profile = _profile(db, user.id)
    profile.preferred_work_type = patch.preferred_work_type.strip()
    profile.preferred_location = patch.preferred_location.strip()
    profile.salary_expectation = patch.salary_expectation.strip()
    profile.updated_at = utcnow()
    db.commit()
    return workspace(db, user)


def complete_step(db: DbSession, user: User, step_id: str) -> CandidateWorkspaceOut:
    profile = _profile(db, user.id)
    step = next((item for item in profile.steps if item.key == step_id), None)
    if not step:
        raise NotFound("That onboarding step is not available.")
    if step.status == "complete":
        return workspace(db, user)
    if step.status == "upcoming":
        raise Conflict("Complete the current onboarding step first.")
    if step_id == "profile" and not (
        profile.headline.strip() and profile.location.strip() and profile.skills
    ):
        raise Conflict("Add a headline, location, and at least one skill first.")
    if step_id == "preferences" and not (
        profile.preferred_work_type.strip() and profile.preferred_location.strip()
    ):
        raise Conflict("Choose a work type and preferred location first.")
    if step_id == "documents" and not profile.documents:
        raise Conflict("Upload at least one document first.")
    step.status = "complete"
    step.completed_at = utcnow()
    _advance_steps(profile)
    if all(item.status == "complete" for item in profile.steps):
        profile.stage = "review"
    _log(
        db,
        profile.agency_id,
        user.id,
        f"{user.name} completed {step_id} onboarding",
        "Onboarding progress updated",
    )
    db.commit()
    return workspace(db, user)


def _matches_signature(content_type: str, content: bytes) -> bool:
    if content_type == "application/pdf":
        return content.startswith(b"%PDF")
    if content_type.endswith("wordprocessingml.document"):
        return content.startswith(b"PK\x03\x04")
    return content.startswith(b"\xd0\xcf\x11\xe0")


def add_document(
    db: DbSession,
    user: User,
    filename: str,
    content_type: str,
    content: bytes,
) -> CandidateWorkspaceOut:
    if content_type not in ALLOWED_DOCUMENT_TYPES:
        raise Conflict("Upload a PDF or Word document.")
    if not content:
        raise Conflict("The uploaded file is empty.")
    if not _matches_signature(content_type, content):
        raise Conflict("That file does not look like a PDF or Word document.")
    if len(content) > get_settings().max_upload_bytes:
        raise Conflict("The document is larger than 10 MB.")
    _profile(db, user.id)  # Ensure the account owns a candidate profile.
    document_id = str(uuid4())
    suffix = Path(filename).suffix.lower() or ".pdf"
    folder = get_settings().document_path / user.id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{document_id}{suffix}"
    path.write_bytes(content)
    db.add(
        Document(
            id=document_id,
            candidate_id=user.id,
            filename=Path(filename).name,
            content_type=content_type,
            size=len(content),
            storage_path=str(path),
        )
    )
    db.commit()
    return workspace(db, user)


def get_document(db: DbSession, user: User, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise NotFound("That document was not found.")
    if document.candidate_id != user.id:
        raise Forbidden("You do not have access to that document.")
    return document


def delete_document(db: DbSession, user: User, document_id: str) -> CandidateWorkspaceOut:
    document = get_document(db, user, document_id)
    if document.candidate_id != user.id:
        raise Forbidden("Only the candidate can remove this document.")
    path = Path(document.storage_path)
    db.delete(document)
    db.commit()
    if path.exists():
        path.unlink()
    return workspace(db, user)


def candidate_agency_candidates(db: DbSession, agency_id: str) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.agency_id == agency_id,
                Membership.active.is_(True),
                User.role == "candidate",
                User.is_active.is_(True),
            )
        )
    )
