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
    key: str = Field(min_length=1, max_length=40)
    name: str = ""
    is_start: bool = False
    is_terminal: bool = False
    approval_policy: Literal["all", "any"] = "all"
    fields: list[FieldIn] = []


class TransitionIn(BaseModel):
    from_key: str
    to_key: str
    condition: dict | None = None
    priority: int = 0
    is_default: bool = False


class WorkflowIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    steps: list[StepIn] = []
    transitions: list[TransitionIn] = []


class WorkflowCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""


class ReviewIn(BaseModel):
    comment: str = ""


class ProjectIn(BaseModel):
    workflow_id: int
    name: str = Field(min_length=1, max_length=200)
    assignments: dict[str, int]
    approvers: dict[str, list[int]] = {}


class ValuesIn(BaseModel):
    values: dict[str, Any] = {}


class DecisionIn(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str = ""
