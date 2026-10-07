from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# Plain JSON on SQLite, JSONB on PostgreSQL.
JSONType = JSON().with_variant(JSONB(), "postgresql")


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
    steps: Mapped[list[WorkflowStep]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowStep.order"
    )
    transitions: Mapped[list[StepTransition]] = relationship(
        cascade="all, delete-orphan", order_by="StepTransition.priority"
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (UniqueConstraint("workflow_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = cascade_fk("workflows.id", index=True)
    key: Mapped[str] = mapped_column(String(40))  # "4", "5A", "5B"
    name: Mapped[str] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_start: Mapped[bool] = mapped_column(Boolean, default=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_policy: Mapped[str] = mapped_column(String(10), default="all")  # all | any

    workflow: Mapped[Workflow] = relationship(back_populates="steps")
    fields: Mapped[list[StepField]] = relationship(
        back_populates="step", cascade="all, delete-orphan", order_by="StepField.order"
    )


class StepField(Base):
    __tablename__ = "step_fields"
    __table_args__ = (UniqueConstraint("step_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    step_id: Mapped[int] = cascade_fk("workflow_steps.id", index=True)
    key: Mapped[str] = mapped_column(String(60))
    type: Mapped[str] = mapped_column(String(30))
    label: Mapped[str] = mapped_column(String(200))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSONType, default=dict)
    order: Mapped[int] = mapped_column(Integer, default=0)

    step: Mapped[WorkflowStep] = relationship(back_populates="fields")


class StepTransition(Base):
    __tablename__ = "step_transitions"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = cascade_fk("workflows.id", index=True)
    from_step_id: Mapped[int] = cascade_fk("workflow_steps.id")
    to_step_id: Mapped[int] = cascade_fk("workflow_steps.id")
    condition: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|completed|archived
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped[Workflow] = relationship()
    creator: Mapped[User] = relationship()
    instances: Mapped[list[StepInstance]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="StepInstance.id"
    )
    assignments: Mapped[list[ProjectAssignment]] = relationship(cascade="all, delete-orphan")
    approver_assignments: Mapped[list[ProjectApprover]] = relationship(cascade="all, delete-orphan")


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"
    __table_args__ = (UniqueConstraint("project_id", "step_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = cascade_fk("projects.id", index=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("workflow_steps.id"))
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)


class ProjectApprover(Base):
    __tablename__ = "project_approvers"
    __table_args__ = (UniqueConstraint("project_id", "step_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = cascade_fk("projects.id", index=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("workflow_steps.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)


class StepInstance(Base):
    __tablename__ = "step_instances"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = cascade_fk("projects.id", index=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("workflow_steps.id"))
    assignee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # in_progress | submitted | approved   (a rejection sends it back to in_progress, round + 1)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", index=True)
    round: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="instances")
    step: Mapped[WorkflowStep] = relationship()
    assignee: Mapped[User] = relationship()
    approvals: Mapped[list[StepApproval]] = relationship(
        cascade="all, delete-orphan", order_by="StepApproval.id"
    )
    values: Mapped[list[FieldValue]] = relationship(cascade="all, delete-orphan")


class StepApproval(Base):
    __tablename__ = "step_approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = cascade_fk("step_instances.id", index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    round: Mapped[int] = mapped_column(Integer, default=1)
    decision: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected
    comment: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship()


class FieldValue(Base):
    __tablename__ = "field_values"
    __table_args__ = (UniqueConstraint("instance_id", "field_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    instance_id: Mapped[int] = cascade_fk("step_instances.id", index=True)
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
    instance_id: Mapped[int | None] = mapped_column(ForeignKey("step_instances.id", ondelete="SET NULL"), nullable=True)
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
