from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from .common import ApiModel

CandidateStage = Literal["onboarding", "review", "interview", "ready"]
TeamRole = Literal["employee", "supervisor"]


class StaffCandidateOut(ApiModel):
    id: str
    name: str
    headline: str
    location: str
    status: str
    onboarding: int
    assigned_to: str | None
    skills: list[str]
    updated_at: datetime


class TeamMemberOut(ApiModel):
    id: str
    name: str
    email: str
    role: str
    team: str
    workload: int
    active: bool


class ActivityOut(ApiModel):
    id: str
    title: str
    detail: str
    tone: str
    created_at: datetime


class StaffStatsOut(ApiModel):
    active_candidates: int
    open_assignments: int
    onboarding_in_progress: int
    application_activity: int


class StaffWorkspaceOut(ApiModel):
    stats: StaffStatsOut
    candidates: list[StaffCandidateOut]
    team_members: list[TeamMemberOut]
    teams: list[str]
    activity: list[ActivityOut]


class AssignmentInput(ApiModel):
    member_id: str | None = None


class StageInput(ApiModel):
    stage: CandidateStage


class MemberCreateInput(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: TeamRole
    team: str = Field(min_length=1, max_length=120)


class MemberCreatedOut(ApiModel):
    workspace: StaffWorkspaceOut
    temporary_password: str


class MemberPatch(ApiModel):
    role: TeamRole | None = None
    team: str | None = Field(default=None, max_length=120)
    active: bool | None = None
