from typing import Literal

from pydantic import EmailStr, Field, field_validator

from .common import ApiModel

Role = Literal["candidate", "employee", "supervisor", "platform_admin"]
Workspace = Literal["candidate", "staff", "platform"]


class AgencyOut(ApiModel):
    id: str
    name: str


class SessionUserOut(ApiModel):
    id: str
    name: str
    email: str
    role: Role
    label: str
    workspace: Workspace
    agencies: list[AgencyOut]


class SessionOut(ApiModel):
    user: SessionUserOut
    agency: AgencyOut | None


class RegisterInput(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    referral_token: str | None = Field(default=None, max_length=255)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Enter your name.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        # Preserve password bytes, but reject a value that is only whitespace.
        if not value.strip():
            raise ValueError("Choose a password that is not only spaces.")
        return value


class LoginInput(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    agency_id: str | None = None


class DemoLoginInput(ApiModel):
    persona_id: str


class ContextInput(ApiModel):
    agency_id: str


class PasswordChangeInput(ApiModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class DemoPersonaOut(ApiModel):
    id: str
    name: str
    role: Role
    label: str
    description: str
    workspace: Workspace
