from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import ApiModel

WorkType = Literal["Remote", "Hybrid", "On-site", "Flexible"]
ExperienceLevel = Literal["Entry", "Junior", "Mid", "Senior", "Lead", "Executive"]

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


class ProfileOut(ApiModel):
    name: str
    email: str
    headline: str
    summary: str
    phone: str
    location: str
    linkedin_url: str
    portfolio_url: str
    current_title: str
    experience_level: str
    completion: int
    stage: str


class PreferenceOut(ApiModel):
    work_type: str
    preferred_location: str
    salary_expectation: str
    availability: str
    willing_to_relocate: bool


class ExperienceOut(ApiModel):
    id: str
    company: str
    title: str
    location: str
    start_date: str
    end_date: str | None
    current: bool
    description: str


class EducationOut(ApiModel):
    id: str
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: int | None
    grade: str


class OnboardingStepOut(ApiModel):
    id: str
    title: str
    description: str
    status: str


class DocumentOut(ApiModel):
    id: str
    filename: str
    size: int
    created_at: datetime


class ReferralContextOut(ApiModel):
    agency_name: str
    referrer_name: str
    label: str


class CandidateWorkspaceOut(ApiModel):
    profile: ProfileOut
    preferences: PreferenceOut | None
    experiences: list[ExperienceOut]
    education: list[EducationOut]
    skills: list[str]
    onboarding: list[OnboardingStepOut]
    next_steps: list[str]
    documents: list[DocumentOut]
    onboarding_complete: bool
    referral: ReferralContextOut | None


class PersonalStepInput(ApiModel):
    phone: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=160)
    headline: str = Field(default="", max_length=160)
    summary: str = Field(default="", max_length=1000)
    linkedin_url: str = Field(default="", max_length=255)
    portfolio_url: str = Field(default="", max_length=255)

    @field_validator("linkedin_url", "portfolio_url")
    @classmethod
    def validate_link(cls, value: str) -> str:
        value = value.strip()
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("Links must start with http:// or https://.")
        return value


class ExperienceInput(ApiModel):
    id: str | None = Field(default=None, max_length=36)
    company: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=160)
    location: str = Field(default="", max_length=160)
    start_date: str = Field(pattern=MONTH_PATTERN)
    end_date: str | None = Field(default=None, pattern=MONTH_PATTERN)
    current: bool = False
    description: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_dates(self) -> ExperienceInput:
        if self.current:
            self.end_date = None
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before the start date.")
        return self


class PreferenceInput(ApiModel):
    work_type: WorkType
    preferred_location: str = Field(default="", max_length=160)
    salary_expectation: str = Field(default="", max_length=80)
    availability: str = Field(default="", max_length=80)
    willing_to_relocate: bool = False


class ProfessionalStepInput(ApiModel):
    current_title: str = Field(default="", max_length=120)
    experience_level: ExperienceLevel
    skills: list[str] = Field(default_factory=list, max_length=30)
    experiences: list[ExperienceInput] = Field(default_factory=list, max_length=10)
    preferences: PreferenceInput

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            name = value.strip()
            if not name or len(name) > 80 or name.lower() in seen:
                continue
            seen.add(name.lower())
            result.append(name)
        return result


class EducationInput(ApiModel):
    id: str | None = Field(default=None, max_length=36)
    institution: str = Field(min_length=1, max_length=160)
    degree: str = Field(min_length=1, max_length=160)
    field_of_study: str = Field(default="", max_length=160)
    start_year: int = Field(ge=1950, le=2100)
    end_year: int | None = Field(default=None, ge=1950, le=2100)
    grade: str = Field(default="", max_length=40)

    @model_validator(mode="after")
    def validate_years(self) -> EducationInput:
        if self.end_year is not None and self.end_year < self.start_year:
            raise ValueError("End year cannot be before the start year.")
        return self


class AcademicStepInput(ApiModel):
    education: list[EducationInput] = Field(default_factory=list, max_length=10)
