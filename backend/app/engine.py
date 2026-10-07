"""Project step engine: save, submit, approve/reject, branch, complete."""
from sqlalchemy.orm import Session

from .conditions import evaluate
from .errors import EngineError
from .fields import FieldError, get_type
from .models import (
    AuditLog, FieldValue, Project, ProjectAssignment, ProjectApprover, StepApproval,
    StepInstance, User, now,
)


def audit(db: Session, user: User | None, action: str, entity: str, entity_id: int | None, payload=None):
    db.add(AuditLog(actor_id=user.id if user else None, action=action, entity_type=entity,
                    entity_id=entity_id, payload=payload))


def values_by_key(inst: StepInstance) -> dict:
    return {v.field.key: v.value for v in inst.values}


def _new_instance(db: Session, project: Project, step_id: int) -> StepInstance:
    assignment = next((a for a in project.assignments if a.step_id == step_id), None)
    if not assignment:
        raise EngineError(500, "No assignee configured for a step on the chosen path")
    inst = StepInstance(project_id=project.id, step_id=step_id, assignee_id=assignment.assignee_id,
                        status="in_progress", round=1)
    db.add(inst)
    db.flush()
    project.instances.append(inst)
    return inst


def start_project(db: Session, project: Project) -> StepInstance:
    start = next(s for s in project.workflow.steps if s.is_start)
    return _new_instance(db, project, start.id)


def save_values(db: Session, inst: StepInstance, values: dict) -> None:
    fields = {f.key: f for f in inst.step.fields}
    errors = []
    for key, raw in values.items():
        field = fields.get(key)
        if not field:
            raise EngineError(422, f"Unknown field '{key}'")
        existing = next((v for v in inst.values if v.field_id == field.id), None)
        if raw in (None, "", []):
            if existing:
                inst.values.remove(existing)
            continue
        try:
            clean = get_type(field.type).clean_value(
                raw, field.config or {}, {"db": db, "instance_id": inst.id})
        except FieldError as e:
            errors.append(f"{field.label}: {e}")
            continue
        if existing:
            existing.value = clean
        else:
            inst.values.append(FieldValue(instance_id=inst.id, field_id=field.id, value=clean))
    if errors:
        raise EngineError(422, errors)
    db.flush()


def _check_actor(inst: StepInstance, user: User):
    if inst.assignee_id != user.id and user.role != "admin":
        raise EngineError(403, "Only the assigned user can edit this step")
    if inst.status != "in_progress":
        raise EngineError(400, "This step is not open for editing")


def save_draft(db: Session, inst: StepInstance, user: User, values: dict):
    _check_actor(inst, user)
    save_values(db, inst, values)


def submit(db: Session, inst: StepInstance, user: User, values: dict):
    _check_actor(inst, user)
    if values:
        save_values(db, inst, values)
    filled = {v.field_id for v in inst.values}
    missing = [f.label for f in inst.step.fields if f.required and f.id not in filled]
    if missing:
        raise EngineError(422, [f"{label}: required" for label in missing])
    inst.status = "submitted"
    inst.submitted_at = now()
    approver_ids = [a.user_id for a in inst.project.approver_assignments if a.step_id == inst.step_id]
    audit(db, user, "step.submitted", "step_instance", inst.id, {"round": inst.round})
    if not approver_ids:  # no approvers configured for this step: auto-approve
        _finalize(db, inst)
        return
    for uid in approver_ids:
        inst.approvals.append(StepApproval(instance_id=inst.id, user_id=uid, round=inst.round))
    db.flush()


def decide(db: Session, inst: StepInstance, user: User, decision: str, comment: str):
    if inst.status != "submitted":
        raise EngineError(400, "This step is not waiting for approval")
    if decision == "rejected" and not comment.strip():
        raise EngineError(422, ["A comment is required when rejecting"])
    rows = [a for a in inst.approvals if a.round == inst.round]
    mine = next((a for a in rows if a.user_id == user.id), None)
    override = False
    if mine is None:
        if user.role != "admin":
            raise EngineError(403, "You are not an approver for this step")
        override = True  # admin acting on behalf of the approvers
        mine = StepApproval(instance_id=inst.id, user_id=user.id, round=inst.round)
        inst.approvals.append(mine)
    elif mine.decision != "pending":
        raise EngineError(400, "You have already decided on this step")
    mine.decision, mine.comment, mine.decided_at = decision, comment.strip(), now()
    audit(db, user, f"step.{decision}", "step_instance", inst.id, {"round": inst.round})

    if decision == "rejected":  # back to the assignee for rework
        inst.status = "in_progress"
        inst.round += 1
        db.flush()
        return
    rows = [a for a in inst.approvals if a.round == inst.round]
    if override or inst.step.approval_policy == "any" or all(a.decision == "approved" for a in rows):
        _finalize(db, inst)
    else:
        db.flush()


def _finalize(db: Session, inst: StepInstance):
    inst.status = "approved"
    inst.completed_at = now()
    db.flush()
    advance(db, inst)


def advance(db: Session, inst: StepInstance):
    project, step = inst.project, inst.step
    outgoing = sorted((t for t in project.workflow.transitions if t.from_step_id == step.id),
                      key=lambda t: t.priority)
    if step.is_terminal or not outgoing:
        if not step.is_terminal:
            raise EngineError(500, f"Step {step.key} has no outgoing transition")
        project.status = "completed"
        audit(db, None, "project.completed", "project", project.id)
        db.flush()
        return
    values = values_by_key(inst)
    chosen = default = None
    for t in outgoing:
        is_default = t.is_default or (len(outgoing) == 1 and not t.condition)
        if is_default:
            default = default or t
        elif evaluate(t.condition, values):
            chosen = t
            break
    chosen = chosen or default
    if not chosen:
        raise EngineError(400, f"No transition matched after step {step.key}")
    nxt = _new_instance(db, project, chosen.to_step_id)
    audit(db, None, "project.advanced", "project", project.id,
          {"from": step.key, "to_step_id": chosen.to_step_id, "instance": nxt.id})
    db.flush()
