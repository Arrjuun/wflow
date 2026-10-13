from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserPatch(BaseModel):
    status: Literal["active", "disabled"] | None = None
    role: Literal["admin", "user"] | None = None


class FieldIn(BaseModel):
    key: str = Field(min_length=1, max_length=60)
    type: str
    label: str = ""
    required: bool = False
    config: dict = {}


class StepIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    fields: list[FieldIn] = []


class PhaseIn(BaseModel):
    key: str = Field(min_length=1, max_length=40)
    name: str = ""
    is_start: bool = False
    is_terminal: bool = False
    requires_gate: bool = True
    steps: list[StepIn] = []


class TransitionIn(BaseModel):
    from_key: str
    to_key: str
    condition: dict | None = None
    is_default: bool = False


class WorkflowIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    phases: list[PhaseIn] = []
    transitions: list[TransitionIn] = []


class WorkflowCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""


class ReviewIn(BaseModel):
    comment: str = ""


class MemberIn(BaseModel):
    user_id: int
    role: Literal["author", "approver", "authorizer"]


class ProjectDetailsIn(BaseModel):
    """Name plus any details the project creator defines (e.g. start date, FEM registration number)."""
    name: str = Field(min_length=1, max_length=200)
    detail_fields: list[FieldIn] = []
    detail_values: dict[str, Any] = {}


class ProjectIn(ProjectDetailsIn):
    workflow_id: int
    members: list[MemberIn]


class MembersIn(BaseModel):
    members: list[MemberIn]


class ReferenceIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(default="", max_length=1000)
    file_id: int | None = None
    note: str = ""


class LessonIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = ""


class ValuesIn(BaseModel):
    values: dict[str, Any] = {}


class DecisionIn(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str = ""
