"""Project engine.

Phase:  in_progress -> (all steps approved) -> awaiting_signoff -> approved -> next phase
Step:   in_progress -> submitted -> approved          (rejected: back to in_progress, round + 1)

Authors fill and submit steps, approvers approve each step (all must approve), authorizers
sign off the phase gate (any one). Admins can do all of these on any project; an admin's
approval or sign-off counts as final.
"""
from sqlalchemy.orm import Session

from .conditions import choose
from .errors import EngineError
from .fields import FieldError, clean_config, get_type
from .models import (AuditLog, FieldValue, GateDecision, PhaseInstance, Project, StepDecision, StepInstance,
                     User, now)

OPEN = ("in_progress", "awaiting_signoff")


def audit(db: Session, user: User | None, action: str, entity: str, entity_id: int | None, payload=None):
    db.add(AuditLog(actor_id=user.id if user else None, action=action, entity_type=entity,
                    entity_id=entity_id, payload=payload))


def values_by_key(inst: PhaseInstance) -> dict:
    return {v.field.key: v.value for v in inst.values}


def current_instance(project: Project) -> PhaseInstance | None:
    return next((i for i in reversed(project.instances) if i.status in OPEN), None)


def is_admin(user: User) -> bool:
    return user.role == "admin"


def is_author(project: Project, user: User) -> bool:
    """Project team, or an admin (admins can do everything)."""
    return is_admin(user) or user.id in project.member_ids("author")


def _require_active(project: Project):
    if project.status != "active":
        raise EngineError(400, "Project is not active")


# ------------------------------------------------------------------ project details (defined by the creator)
def clean_details(db: Session, project: Project, fields: list[dict], values: dict) -> tuple[list, dict]:
    keys, clean_fields, errors = set(), [], []
    for f in fields:
        key, ftype = str(f.get("key", "")).strip(), f.get("type", "text")
        label = str(f.get("label", "")).strip() or key
        if not key or key in keys:
            errors.append(f"Detail '{label or '?'}' needs a unique key")
            continue
        try:
            config = clean_config(ftype, f.get("config"))
        except (FieldError, ValueError, TypeError) as e:
            errors.append(f"{label}: {e}")
            continue
        keys.add(key)
        clean_fields.append({"key": key, "type": ftype, "label": label, "config": config,
                             "required": bool(f.get("required")) and get_type(ftype).has_value})
    clean_values = {}
    for f in clean_fields:
        ftype = get_type(f["type"])
        raw = values.get(f["key"])
        if not ftype.has_value:
            continue
        if raw in (None, "", []):
            if f["required"]:
                errors.append(f"{f['label']} is required")
            continue
        try:
            v = ftype.clean_value(raw, f["config"], {"db": db, "project_id": project.id})
        except FieldError as e:
            errors.append(f"{f['label']}: {e}")
            continue
        if v is not None:
            clean_values[f["key"]] = v
        elif f["required"]:
            errors.append(f"{f['label']} is required")
    if errors:
        raise EngineError(422, errors)
    return clean_fields, clean_values


# ------------------------------------------------------------------ phases and steps
def _new_phase(db: Session, project: Project, phase_id: int) -> PhaseInstance:
    inst = PhaseInstance(project_id=project.id, phase_id=phase_id, status="in_progress", round=1)
    db.add(inst)
    db.flush()
    project.instances.append(inst)
    for step in inst.phase.steps:
        inst.steps.append(StepInstance(phase_instance_id=inst.id, step_id=step.id, status="in_progress"))
    db.flush()
    return inst


def start_project(db: Session, project: Project) -> PhaseInstance:
    start = next(p for p in project.workflow.phases if p.is_start)
    return _new_phase(db, project, start.id)


def save_values(db: Session, inst: PhaseInstance, user: User, values: dict, only_step: StepInstance | None = None):
    """Save draft values. Only fields of steps that are still open can change."""
    project = inst.project
    _require_active(project)
    if not is_author(project, user):
        raise EngineError(403, "Only the project team (authors) or an admin can fill in steps")
    if inst.status != "in_progress":
        raise EngineError(400, "This phase is not open for editing")
    open_steps = {si.step_id: si for si in inst.steps if si.status == "in_progress"}
    fields = {f.key: f for s in inst.phase.steps for f in s.fields}
    errors = []
    for key, raw in values.items():
        field = fields.get(key)
        if not field:
            raise EngineError(422, f"Unknown field '{key}'")
        if only_step and field.step_id != only_step.step_id:
            continue
        ftype = get_type(field.type)
        if not ftype.has_value:
            continue
        if field.step_id not in open_steps:
            continue  # submitted/approved steps are locked; their values are left untouched
        existing = next((v for v in inst.values if v.field_id == field.id), None)
        clean = None
        if raw not in (None, "", []):
            try:
                clean = ftype.clean_value(raw, field.config or {}, {"db": db, "project_id": project.id})
            except FieldError as e:
                errors.append(f"{field.label}: {e}")
                continue
        if clean is None:
            if existing:
                inst.values.remove(existing)
        elif existing:
            existing.value = clean
        else:
            inst.values.append(FieldValue(instance_id=inst.id, field_id=field.id, value=clean))
    if errors:
        raise EngineError(422, errors)
    db.flush()


def submit_step(db: Session, si: StepInstance, user: User, values: dict):
    inst = si.phase_instance
    if si.status != "in_progress":
        raise EngineError(400, "This step has already been submitted")
    save_values(db, inst, user, values or {}, only_step=si)
    filled = {v.field_id for v in inst.values}
    missing = [f"{f.label} is required" for f in si.step.fields
               if f.required and get_type(f.type).has_value and f.id not in filled]
    if missing:
        raise EngineError(422, missing)
    si.status, si.submitted_at = "submitted", now()
    audit(db, user, "step.submitted", "step_instance", si.id, {"round": si.round})
    evaluate_step(db, si)


def _round(si: StepInstance):
    return [d for d in si.decisions if d.round == si.round]


def evaluate_step(db: Session, si: StepInstance):
    """Approve a submitted step once every current project approver has approved it."""
    if si.status != "submitted":
        return
    approvers = si.phase_instance.project.member_ids("approver")
    approved = {d.user_id for d in _round(si) if d.decision == "approved"}
    if not approvers or approved & approvers:
        si.status, si.completed_at = "approved", now()
        db.flush()
        _check_phase(db, si.phase_instance)
    else:
        db.flush()


def can_decide_step(si: StepInstance, user: User) -> bool:
    project = si.phase_instance.project
    allowed = is_admin(user) or user.id in project.member_ids("approver")
    return (project.status == "active" and si.status == "submitted" and allowed
            and user.id not in {d.user_id for d in _round(si)})


def decide_step(db: Session, si: StepInstance, user: User, decision: str, comment: str):
    if not can_decide_step(si, user):
        raise EngineError(403, "Only the project's approvers or an admin can review a submitted step, once per round")
    if decision == "rejected" and not comment.strip():
        raise EngineError(422, ["Add a comment explaining what needs to change"])
    si.decisions.append(StepDecision(step_instance_id=si.id, user_id=user.id, round=si.round,
                                     decision=decision, comment=comment.strip()))
    audit(db, user, f"step.{decision}", "step_instance", si.id, {"round": si.round})
    if decision == "rejected":
        si.status, si.round = "in_progress", si.round + 1
        db.flush()
        return
    if is_admin(user) and user.id not in si.phase_instance.project.member_ids("approver"):
        si.status, si.completed_at = "approved", now()  # admin override: approves the step outright
        db.flush()
        _check_phase(db, si.phase_instance)
        return
    evaluate_step(db, si)


def _check_phase(db: Session, inst: PhaseInstance):
    if inst.status != "in_progress" or any(s.status != "approved" for s in inst.steps):
        return
    if inst.phase.requires_gate and inst.project.member_ids("authorizer"):
        inst.status, inst.submitted_at = "awaiting_signoff", now()
        db.flush()
    else:
        _finalize(db, inst)


def can_sign_off(inst: PhaseInstance, user: User) -> bool:
    return (inst.project.status == "active" and inst.status == "awaiting_signoff"
            and (is_admin(user) or user.id in inst.project.member_ids("authorizer")))


def sign_off(db: Session, inst: PhaseInstance, user: User, decision: str, comment: str):
    if not can_sign_off(inst, user):
        raise EngineError(403, "Only the project's authorizers or an admin can sign off this gate review")
    if decision == "rejected" and not comment.strip():
        raise EngineError(422, ["Add a comment explaining what needs to change"])
    role = "authorizer" if user.id in inst.project.member_ids("authorizer") else "admin"
    inst.decisions.append(GateDecision(instance_id=inst.id, user_id=user.id, role=role, round=inst.round,
                                       decision=decision, comment=comment.strip()))
    audit(db, user, f"gate.{decision}", "phase_instance", inst.id, {"round": inst.round})
    if decision == "rejected":  # whole phase goes back to the authors; values are kept
        inst.status, inst.round = "in_progress", inst.round + 1
        for si in inst.steps:
            si.status, si.round, si.completed_at = "in_progress", si.round + 1, None
        db.flush()
        return
    _finalize(db, inst)


def _finalize(db: Session, inst: PhaseInstance):
    inst.status, inst.completed_at = "approved", now()
    db.flush()
    project, phase = inst.project, inst.phase
    outgoing = [t for t in project.workflow.transitions if t.from_phase_id == phase.id]
    if phase.is_terminal or not outgoing:
        project.status = "completed"
        audit(db, None, "project.completed", "project", project.id)
        db.flush()
        return
    paths = [{"t": t, "condition": t.condition, "is_default": t.is_default} for t in outgoing]
    chosen = choose(paths, values_by_key(inst))
    if not chosen:
        raise EngineError(400, f"No path matched after {phase.name}")
    nxt = _new_phase(db, project, chosen["t"].to_phase_id)
    audit(db, None, "project.advanced", "project", project.id, {"from": phase.key, "instance": nxt.id})


def reevaluate(db: Session, project: Project):
    """Called after the team changes: approver/authorizer sets may now be satisfied."""
    inst = current_instance(project)
    if not inst:
        return
    if inst.status == "in_progress":
        for si in list(inst.steps):
            if inst.status != "in_progress":
                break
            evaluate_step(db, si)
        _check_phase(db, inst)
    elif inst.status == "awaiting_signoff" and not project.member_ids("authorizer"):
        _finalize(db, inst)
