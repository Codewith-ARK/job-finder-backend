from datetime import datetime

from pydantic import Field

from .common import ApiModel


class ProfileOut(ApiModel):
    name: str
    email: str
    headline: str
    location: str
    skills: list[str]
    completion: int
    preferred_work_type: str
    preferred_location: str
    salary_expectation: str


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


class CandidateWorkspaceOut(ApiModel):
    profile: ProfileOut
    onboarding: list[OnboardingStepOut]
    next_steps: list[str]
    documents: list[DocumentOut]


class ProfilePatch(ApiModel):
    headline: str = Field(max_length=160)
    location: str = Field(max_length=160)
    skills: list[str] = Field(default_factory=list, max_length=30)


class PreferencesPatch(ApiModel):
    preferred_work_type: str = Field(max_length=40)
    preferred_location: str = Field(max_length=160)
    salary_expectation: str = Field(max_length=80)
