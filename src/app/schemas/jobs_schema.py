from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from .common import ApiModel

JobStatus = Literal["open", "closed"]
ApplicationStatus = Literal["submitted", "review", "interview", "offer", "closed"]
WorkType = Literal["Remote", "Hybrid", "On-site"]
JobTag = Annotated[str, StringConstraints(max_length=40, strip_whitespace=True)]


class JobOut(ApiModel):
    id: str
    agency_name: str
    title: str
    company: str
    location: str
    work_type: str
    salary: str
    tags: list[str]
    status: str
    posted: datetime
    description: str


class ApplicationOut(ApiModel):
    id: str
    job_id: str
    job_title: str
    company: str
    agency_name: str
    candidate_id: str
    candidate_name: str
    status: str
    submitted_at: datetime
    next_step: str
    updated_at: datetime


class JobsWorkspaceOut(ApiModel):
    jobs: list[JobOut]
    applications: list[ApplicationOut]


class JobInput(ApiModel):
    title: str = Field(min_length=1, max_length=160)
    company: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=160)
    work_type: WorkType
    salary: str = Field(default="", max_length=80)
    tags: list[JobTag] = Field(default_factory=list, max_length=12)
    description: str = Field(default="", max_length=2000)

    @field_validator("title", "company", "location", mode="before")
    @classmethod
    def validate_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("This field is required.")
        return value

    @field_validator("salary", "description", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class JobPatch(ApiModel):
    title: str | None = Field(default=None, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=160)
    work_type: WorkType | None = None
    salary: str | None = Field(default=None, max_length=80)
    tags: list[JobTag] | None = Field(default=None, max_length=12)
    description: str | None = Field(default=None, max_length=2000)
    status: JobStatus | None = None

    @field_validator("title", "company", "location", mode="before")
    @classmethod
    def validate_required_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("This field cannot be blank.")
        return value

    @field_validator("salary", "description", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ApplicationStatusInput(ApiModel):
    status: ApplicationStatus
