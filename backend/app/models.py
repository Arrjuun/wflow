from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# Plain JSON on SQLite, JSONB on PostgreSQL.
JSONType = JSON().with_variant(JSONB(), "postgresql")
ROLES = ("author", "approver", "authorizer")


def now() -> datetime:
    return datetime.now(timezone.utc)


def cascade_fk(target: str, **kw):
    return mapped_column(ForeignKey(target, ondelete="CASCADE"), **kw)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")  # admin | user
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | active | disabled
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


# ---------------------------------------------------------------- workflow template
# Workflow -> Phase (has a gate review) -> Step (a tab) -> Field
class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    # draft | pending_approval | approved | rejected | retired
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    owner: Mapped[User] = relationship(foreign_keys=[created_by])
    phases: Mapped[list[WorkflowPhase]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowPhase.order")
    transitions: Mapped[list[PhaseTransition]] = relationship(
        cascade="all, delete-orphan", order_by="PhaseTransition.order")


class WorkflowPhase(Base):
    __tablename__ = "workflow_phases"
    __table_args__ = (UniqueConstraint("workflow_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = cascade_fk("workflows.id", index=True)
    key: Mapped[str] = mapped_column(String(40))  # "1", "2", "3A"
    name: Mapped[str] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_start: Mapped[bool] = mapped_column(Boolean, default=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_gate: Mapped[bool] = mapped_column(Boolean, default=True)  # False: completes on submit

    workflow: Mapped[Workflow] = relationship(back_populates="phases")
    steps: Mapped[list[WorkflowStep]] = relationship(
        back_populates="phase", cascade="all, delete-orphan", order_by="WorkflowStep.order")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    phase_id: Mapped[int] = cascade_fk("workflow_phases.id", index=True)
    name: Mapped[str] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(Integer, default=0)

    phase: Mapped[WorkflowPhase] = relationship(back_populates="steps")
    fields: Mapped[list[StepField]] = relationship(
        back_populates="step", cascade="all, delete-orphan", order_by="StepField.order")


class StepField(Base):
    __tablename__ = "step_fields"
    id: Mapped[int] = mapped_column(primary_key=True)
    step_id: Mapped[int] = cascade_fk("workflow_steps.id", index=True)
    key: Mapped[str] = mapped_column(String(60))  # unique within the phase (checked in code)
    type: Mapped[str] = mapped_column(String(30))
    label: Mapped[str] = mapped_column(String(200))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSONType, default=dict)
    order: Mapped[int] = mapped_column(Integer, default=0)

    step: Mapped[WorkflowStep] = relationship(back_populates="fields")


class PhaseTransition(Base):
    """Path between phases. Conditional paths are tried in list order; the default path is the fallback."""
    __tablename__ = "phase_transitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = cascade_fk("workflows.id", index=True)
    from_phase_id: Mapped[int] = cascade_fk("workflow_phases.id")
    to_phase_id: Mapped[int] = cascade_fk("workflow_phases.id")
    condition: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------- projects
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # Project details are defined by the project creator: [{key, type, label, required, config}]
    detail_fields: Mapped[list] = mapped_column(JSONType, default=list)
    detail_values: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|completed|archived
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped[Workflow] = relationship()
    creator: Mapped[User] = relationship()
    members: Mapped[list[ProjectMember]] = relationship(cascade="all, delete-orphan", order_by="ProjectMember.id")
    references: Mapped[list[ProjectReference]] = relationship(
        cascade="all, delete-orphan", order_by="ProjectReference.id")
    lessons: Mapped[list[ProjectLesson]] = relationship(
        cascade="all, delete-orphan", order_by="ProjectLesson.id")
    instances: Mapped[list[PhaseInstance]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="PhaseInstance.id")

    def member_ids(self, role: str) -> set[int]:
        return {m.user_id for m in self.members if m.role == role}


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", "role"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = cascade_fk("projects.id", index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # author | approver | authorizer

    user: Mapped[User] = relationship()


class ProjectReference(Base):
    """Reference material added by the project creator. Not part of any approval."""
    __tablename__ = "project_references"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = cascade_fk("projects.id", index=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(1000), default="")
    file_id: Mapped[int | None] = mapped_column(ForeignKey("file_assets.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    file: Mapped[FileAsset | None] = relationship()


class ProjectLesson(Base):
    """Lessons learned, recorded on the project like references. Not part of any approval."""
    __tablename__ = "project_lessons"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = cascade_fk("projects.id", index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    author: Mapped[User] = relationship()


class PhaseInstance(Base):
    __tablename__ = "phase_instances"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = cascade_fk("projects.id", index=True)
    phase_id: Mapped[int] = mapped_column(ForeignKey("workflow_phases.id"))
    # in_progress (steps being filled/approved) -> awaiting_signoff (authorizers) -> approved
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    round: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="instances")
    phase: Mapped[WorkflowPhase] = relationship()
    values: Mapped[list[FieldValue]] = relationship(cascade="all, delete-orphan")
    steps: Mapped[list[StepInstance]] = relationship(
        back_populates="phase_instance", cascade="all, delete-orphan", order_by="StepInstance.id")
    decisions: Mapped[list[GateDecision]] = relationship(cascade="all, delete-orphan", order_by="GateDecision.id")


class StepInstance(Base):
    """One step of a phase in a project. Filled by authors, approved by the project's approvers."""
    __tablename__ = "step_instances"
    id: Mapped[int] = mapped_column(primary_key=True)
    phase_instance_id: Mapped[int] = cascade_fk("phase_instances.id", index=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("workflow_steps.id"))
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)  # in_progress|submitted|approved
    round: Mapped[int] = mapped_column(Integer, default=1)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    phase_instance: Mapped[PhaseInstance] = relationship(back_populates="steps")
    step: Mapped[WorkflowStep] = relationship()
    decisions: Mapped[list[StepDecision]] = relationship(cascade="all, delete-orphan", order_by="StepDecision.id")


class StepDecision(Base):
    __tablename__ = "step_decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    step_instance_id: Mapped[int] = cascade_fk("step_instances.id", index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    round: Mapped[int] = mapped_column(Integer, default=1)
    decision: Mapped[str] = mapped_column(String(20))  # approved | rejected
    comment: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    user: Mapped[User] = relationship()


class GateDecision(Base):
    """Authorizer sign-off of a whole phase."""
    __tablename__ = "gate_decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = cascade_fk("phase_instances.id", index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20), default="authorizer")
    round: Mapped[int] = mapped_column(Integer, default=1)
    decision: Mapped[str] = mapped_column(String(20))  # approved | rejected
    comment: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    user: Mapped[User] = relationship()


class FieldValue(Base):
    __tablename__ = "field_values"
    __table_args__ = (UniqueConstraint("instance_id", "field_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = cascade_fk("phase_instances.id", index=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("step_fields.id"))
    value: Mapped[object] = mapped_column(JSONType)

    field: Mapped[StepField] = relationship()


class FileAsset(Base):
    __tablename__ = "file_assets"
    id: Mapped[int] = mapped_column(primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
