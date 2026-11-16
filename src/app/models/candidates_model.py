from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .common import new_id, utcnow
from .users_model import User  # noqa: F401  (relationship target)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # A candidate does not need an agency. When a referral creates the account this
    # records the referring agency; memberships remain the authorization source.
    agency_id: Mapped[str | None] = mapped_column(
        ForeignKey("agencies.id", ondelete="SET NULL"), nullable=True
    )
    headline: Mapped[str] = mapped_column(String(160), default="")
    summary: Mapped[str] = mapped_column(String(1000), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    location: Mapped[str] = mapped_column(String(160), default="")
    linkedin_url: Mapped[str] = mapped_column(String(255), default="")
    portfolio_url: Mapped[str] = mapped_column(String(255), default="")
    current_title: Mapped[str] = mapped_column(String(120), default="")
    experience_level: Mapped[str] = mapped_column(String(40), default="")
    stage: Mapped[str] = mapped_column(String(20), default="onboarding")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship()

    steps: Mapped[list[OnboardingStep]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="OnboardingStep.position",
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    preferences: Mapped[CandidatePreference | None] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", uselist=False
    )
    experiences: Mapped[list[CandidateExperience]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateExperience.start_date.desc()",
    )
    education: Mapped[list[CandidateEducation]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateEducation.start_year.desc()",
    )
    skills: Mapped[list[CandidateSkill]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateSkill.name",
    )


class CandidatePreference(Base):
    __tablename__ = "candidate_preferences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    work_type: Mapped[str] = mapped_column(String(40), default="")
    preferred_location: Mapped[str] = mapped_column(String(160), default="")
    salary_expectation: Mapped[str] = mapped_column(String(80), default="")
    availability: Mapped[str] = mapped_column(String(80), default="")
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="preferences")


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), index=True
    )
    company: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    location: Mapped[str] = mapped_column(String(160), default="")
    start_date: Mapped[str] = mapped_column(String(7), default="")
    end_date: Mapped[str | None] = mapped_column(String(7), nullable=True)
    current: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="experiences")


class CandidateEducation(Base):
    __tablename__ = "candidate_education"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), index=True
    )
    institution: Mapped[str] = mapped_column(String(160), nullable=False)
    degree: Mapped[str] = mapped_column(String(160), nullable=False)
    field_of_study: Mapped[str] = mapped_column(String(160), default="")
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grade: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="education")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (UniqueConstraint("candidate_id", "name", name="uq_candidate_skill"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="skills")


class OnboardingStep(Base):
    __tablename__ = "onboarding_steps"
    __table_args__ = (UniqueConstraint("candidate_id", "key", name="uq_candidate_step"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="upcoming")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="steps")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.user_id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    blob_pathname: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="documents")
