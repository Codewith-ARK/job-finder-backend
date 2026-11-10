from datetime import datetime
from typing import Literal

from pydantic import Field

from .common import ApiModel

JobStatus = Literal["open", "closed"]
ApplicationStatus = Literal["submitted", "review", "interview", "offer", "closed"]
WorkType = Literal["Remote", "Hybrid", "On-site"]


class JobOut(ApiModel):
    id: str
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
    salary: str = Field(max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=12)
    description: str = Field(default="", max_length=2000)


class JobPatch(ApiModel):
    title: str | None = Field(default=None, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    location: str | None = Field(default=None, max_length=160)
    work_type: WorkType | None = None
    salary: str | None = Field(default=None, max_length=80)
    tags: list[str] | None = Field(default=None, max_length=12)
    description: str | None = Field(default=None, max_length=2000)
    status: JobStatus | None = None


class ApplicationStatusInput(ApiModel):
    status: ApplicationStatus
