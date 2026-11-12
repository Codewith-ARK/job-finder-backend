from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..models import (
    Activity,
    CandidateEducation,
    CandidateExperience,
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    Document,
    Membership,
    OnboardingStep,
    User,
)
from ..models.common import utcnow
from ..schemas.candidates_schema import (
    AcademicStepInput,
    CandidateWorkspaceOut,
    DocumentOut,
    EducationOut,
    ExperienceOut,
    OnboardingStepOut,
    PersonalStepInput,
    PreferenceOut,
    ProfessionalStepInput,
    ProfileOut,
    ReferralContextOut,
)
from .errors import Conflict, Forbidden, NotFound

ONBOARDING = (
    (
        "personal",
        "Personal details",
        "Tell us who you are and how your team can reach you.",
    ),
    (
        "professional",
        "Professional details",
        "Add your role, experience, skills, and what you are looking for.",
    ),
    (
        "academic",
        "Academic details",
        "Add your education so your profile is complete.",
    ),
    (
        "documents",
        "Documents",
        "Upload your CV and any supporting documents.",
    ),
)
STEP_WEIGHTS = {"personal": 20, "professional": 30, "academic": 25, "documents": 25}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_SKILLS = 30


def _profile_query(user_id: str):
    return (
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.steps),
            selectinload(CandidateProfile.documents),
            selectinload(CandidateProfile.preferences),
            selectinload(CandidateProfile.experiences),
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.skills),
        )
        .where(CandidateProfile.user_id == user_id)
    )


def _profile(db: DbSession, user_id: str) -> CandidateProfile:
    profile = db.scalar(_profile_query(user_id))
    if not profile:
        raise NotFound("A candidate profile has not been created for this account.")
    return profile


def bootstrap_candidate(
    db: DbSession, user: User, agency_id: str | None = None
) -> CandidateProfile:
    profile = CandidateProfile(
        user_id=user.id,
        agency_id=agency_id,
        headline="",
        location="",
    )
    db.add(profile)
    db.add(CandidatePreference(user_id=user.id, work_type="", preferred_location=""))
    for position, (key, _title, _description) in enumerate(ONBOARDING):
        db.add(
            OnboardingStep(
                candidate_id=user.id,
                key=key,
                position=position,
                status="next" if position == 0 else "upcoming",
            )
        )
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
        "personal": [
            "Add your contact details and a short headline.",
            "Add your professional experience and skills.",
            "Upload your CV so your team can prepare.",
        ],
        "professional": [
            "Tell us what kind of work feels right.",
            "Add your academic background.",
            "Upload your CV and supporting documents.",
        ],
        "academic": [
            "Add your highest qualification and institution.",
            "Upload your CV and supporting documents.",
            "Browse roles matched to your profile.",
        ],
        "documents": [
            "Upload your CV and any supporting files.",
            "Check that your profile is current.",
            "Apply to a role that fits your goals.",
        ],
    }[next_step.key]


def _preference_out(profile: CandidateProfile) -> PreferenceOut | None:
    preference = profile.preferences
    if not preference:
        return None
    return PreferenceOut(
        work_type=preference.work_type,
        preferred_location=preference.preferred_location,
        salary_expectation=preference.salary_expectation,
        availability=preference.availability,
        willing_to_relocate=preference.willing_to_relocate,
    )


def workspace(db: DbSession, user: User) -> CandidateWorkspaceOut:
    from . import referrals_service

    profile = _profile(db, user.id)
    documents = sorted(profile.documents, key=lambda item: item.created_at, reverse=True)
    referral = referrals_service.context_for_candidate(db, user.id)
    return CandidateWorkspaceOut(
        profile=ProfileOut(
            name=user.name,
            email=user.email,
            headline=profile.headline,
            summary=profile.summary,
            phone=profile.phone,
            location=profile.location,
            linkedin_url=profile.linkedin_url,
            portfolio_url=profile.portfolio_url,
            current_title=profile.current_title,
            experience_level=profile.experience_level,
            completion=_completion(profile),
            stage=profile.stage,
        ),
        preferences=_preference_out(profile),
        experiences=[
            ExperienceOut(
                id=item.id,
                company=item.company,
                title=item.title,
                location=item.location,
                start_date=item.start_date,
                end_date=item.end_date,
                current=item.current,
                description=item.description,
            )
            for item in profile.experiences
        ],
        education=[
            EducationOut(
                id=item.id,
                institution=item.institution,
                degree=item.degree,
                field_of_study=item.field_of_study,
                start_year=item.start_year,
                end_year=item.end_year,
                grade=item.grade,
            )
            for item in profile.education
        ],
        skills=[item.name for item in profile.skills],
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
        onboarding_complete=all(step.status == "complete" for step in profile.steps),
        referral=ReferralContextOut(**referral) if referral else None,
    )


def _step(profile: CandidateProfile, step_key: str):
    step = next((item for item in profile.steps if item.key == step_key), None)
    if not step:
        raise NotFound("That onboarding step is not available.")
    if step.status == "upcoming":
        raise Conflict("Complete the current onboarding step first.")
    return step


def save_personal(db: DbSession, user: User, payload: PersonalStepInput) -> CandidateWorkspaceOut:
    profile = _profile(db, user.id)
    _step(profile, "personal")
    if "phone" in payload.model_fields_set:
        profile.phone = payload.phone.strip()
    if "location" in payload.model_fields_set:
        profile.location = payload.location.strip()
    if "headline" in payload.model_fields_set:
        profile.headline = payload.headline.strip()
    if "summary" in payload.model_fields_set:
        profile.summary = payload.summary.strip()
    if "linkedin_url" in payload.model_fields_set:
        profile.linkedin_url = payload.linkedin_url.strip()
    if "portfolio_url" in payload.model_fields_set:
        profile.portfolio_url = payload.portfolio_url.strip()
    profile.updated_at = utcnow()
    db.commit()
    return workspace(db, user)


def _replace_experiences(profile: CandidateProfile, payload: ProfessionalStepInput) -> None:
    profile.experiences.clear()
    for item in payload.experiences:
        profile.experiences.append(
            CandidateExperience(
                candidate_id=profile.user_id,
                company=item.company.strip(),
                title=item.title.strip(),
                location=item.location.strip(),
                start_date=item.start_date,
                end_date=None if item.current else item.end_date,
                current=item.current,
                description=item.description.strip(),
            )
        )


def _replace_skills(db: DbSession, profile: CandidateProfile, skills: list[str]) -> None:
    # Flush the removals first: the unique (candidate_id, name) constraint would
    # otherwise reject a replacement that reuses an existing skill name.
    profile.skills.clear()
    db.flush()
    for name in skills[:MAX_SKILLS]:
        profile.skills.append(CandidateSkill(candidate_id=profile.user_id, name=name))


def save_professional(
    db: DbSession, user: User, payload: ProfessionalStepInput
) -> CandidateWorkspaceOut:
    profile = _profile(db, user.id)
    _step(profile, "professional")
    if "current_title" in payload.model_fields_set:
        profile.current_title = payload.current_title.strip()
    if "experience_level" in payload.model_fields_set:
        profile.experience_level = payload.experience_level
    if "skills" in payload.model_fields_set:
        _replace_skills(db, profile, payload.skills)
    if "experiences" in payload.model_fields_set:
        _replace_experiences(profile, payload)
    preference = profile.preferences
    if not preference:
        preference = CandidatePreference(user_id=profile.user_id)
        profile.preferences = preference
    if "work_type" in payload.preferences.model_fields_set:
        preference.work_type = payload.preferences.work_type
    if "preferred_location" in payload.preferences.model_fields_set:
        preference.preferred_location = payload.preferences.preferred_location.strip()
    if "salary_expectation" in payload.preferences.model_fields_set:
        preference.salary_expectation = payload.preferences.salary_expectation.strip()
    if "availability" in payload.preferences.model_fields_set:
        preference.availability = payload.preferences.availability.strip()
    if "willing_to_relocate" in payload.preferences.model_fields_set:
        preference.willing_to_relocate = payload.preferences.willing_to_relocate
    preference.updated_at = utcnow()
    profile.updated_at = utcnow()
    db.commit()
    return workspace(db, user)


def save_academic(db: DbSession, user: User, payload: AcademicStepInput) -> CandidateWorkspaceOut:
    profile = _profile(db, user.id)
    _step(profile, "academic")
    if "education" in payload.model_fields_set:
        profile.education.clear()
        for item in payload.education:
            profile.education.append(
                CandidateEducation(
                    candidate_id=profile.user_id,
                    institution=item.institution.strip(),
                    degree=item.degree.strip(),
                    field_of_study=item.field_of_study.strip(),
                    start_year=item.start_year,
                    end_year=item.end_year,
                    grade=item.grade.strip(),
                )
            )
    profile.updated_at = utcnow()
    db.commit()
    return workspace(db, user)


def _advance_steps(profile: CandidateProfile) -> None:
    next_assigned = False
    for step in profile.steps:
        if step.status == "complete":
            continue
        step.status = "upcoming" if next_assigned else "next"
        next_assigned = True


def _log(db: DbSession, agency_id: str | None, user_id: str, title: str, detail: str) -> None:
    if agency_id is None:
        return
    db.add(
        Activity(
            agency_id=agency_id,
            actor_id=user_id,
            title=title,
            detail=detail,
            tone="info",
        )
    )


def _validate_step(profile: CandidateProfile, step_key: str) -> None:
    if step_key == "personal" and not (
        profile.phone.strip() and profile.location.strip() and profile.headline.strip()
    ):
        raise Conflict("Add your phone, location, and headline first.")
    if step_key == "professional":
        preference = profile.preferences
        if not (
            profile.current_title.strip()
            and profile.experience_level.strip()
            and profile.skills
            and preference
            and preference.work_type.strip()
            and preference.preferred_location.strip()
        ):
            raise Conflict(
                "Add your current title, experience level, skills, and work preference first."
            )
    if step_key == "academic" and not profile.education:
        raise Conflict("Add at least one education entry first.")
    if step_key == "documents" and not profile.documents:
        raise Conflict("Upload at least one document first.")


def complete_step(db: DbSession, user: User, step_id: str) -> CandidateWorkspaceOut:
    profile = _profile(db, user.id)
    step = next((item for item in profile.steps if item.key == step_id), None)
    if not step:
        raise NotFound("That onboarding step is not available.")
    if step.status == "complete":
        return workspace(db, user)
    if step.status == "upcoming":
        raise Conflict("Complete the current onboarding step first.")
    _validate_step(profile, step_id)
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
    _profile(db, user.id)
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
