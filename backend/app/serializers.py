from .access import can_manage_project
from .engine import current_instance
from .fields import get_type
from .models import PhaseInstance, Project, User, Workflow


def iso(d):
    return d.isoformat() if d else None


def user_brief(u: User | None):
    return {"id": u.id, "name": u.name, "email": u.email} if u else None


def user_out(u: User):
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role, "status": u.status,
            "must_change_password": u.must_change_password, "created_at": iso(u.created_at)}


# ------------------------------------------------------------------ workflows
def field_out(f):
    return {"id": f.id, "key": f.key, "type": f.type, "label": f.label, "required": f.required, "config": f.config or {}}


def workflow_summary(wf: Workflow):
    return {"id": wf.id, "title": wf.title, "description": wf.description, "status": wf.status,
            "version": wf.version, "owner": user_brief(wf.owner), "created_at": iso(wf.created_at),
            "phase_count": len(wf.phases)}


def workflow_out(wf: Workflow):
    key_of = {p.id: p.key for p in wf.phases}
    return {
        **workflow_summary(wf),
        "review_comment": wf.review_comment,
        "phases": [{
            "id": p.id, "key": p.key, "name": p.name, "is_start": p.is_start, "is_terminal": p.is_terminal,
            "requires_gate": p.requires_gate,
            "steps": [{"id": s.id, "name": s.name, "fields": [field_out(f) for f in s.fields]} for s in p.steps],
        } for p in wf.phases],
        "transitions": [{"from_key": key_of[t.from_phase_id], "to_key": key_of[t.to_phase_id],
                         "condition": t.condition, "is_default": t.is_default} for t in wf.transitions],
    }


def graph_from_workflow(wf: Workflow):
    key_of = {p.id: p.key for p in wf.phases}
    phases = [{"key": p.key, "name": p.name, "is_start": p.is_start, "is_terminal": p.is_terminal,
               "steps": [{"name": s.name, "fields": [
                   {"key": f.key, "label": f.label, "type": f.type, "conditionable": get_type(f.type).conditionable}
                   for f in s.fields]} for s in p.steps]} for p in wf.phases]
    transitions = [{"from_key": key_of[t.from_phase_id], "to_key": key_of[t.to_phase_id],
                    "condition": t.condition, "is_default": t.is_default} for t in wf.transitions]
    return phases, transitions


# ------------------------------------------------------------------ projects
def stage_text(p: Project) -> str:
    if p.status in ("completed", "archived"):
        return p.status.capitalize()
    inst = current_instance(p)
    if not inst:
        return "Not started"
    name = inst.phase.name
    if inst.status == "awaiting_signoff":
        return f"{name} completed, gate review sign-off pending"
    done = sum(1 for s in inst.steps if s.status == "approved")
    waiting = sum(1 for s in inst.steps if s.status == "submitted")
    text = f"{name}: {done} of {len(inst.steps)} steps approved"
    return text + (f", {waiting} awaiting approval" if waiting else "")


def progress(p: Project) -> int:
    """Approved steps out of the steps on the path taken so far plus the default path ahead."""
    if p.status in ("completed", "archived"):
        return 100
    wf = p.workflow
    phases = {ph.id: ph for ph in wf.phases}
    done = sum(1 for i in p.instances for s in i.steps if s.status == "approved")
    inst = current_instance(p)
    total = sum(len(i.steps) for i in p.instances)
    node, seen = (inst.phase if inst else None), set()
    while node is not None and node.id not in seen:  # follow default paths to an end phase
        seen.add(node.id)
        if node.is_terminal:
            break
        outs = [t for t in wf.transitions if t.from_phase_id == node.id]
        nxt = next((t for t in outs if t.is_default), outs[0] if len(outs) == 1 else None)
        node = phases.get(nxt.to_phase_id) if nxt else None
        if node is not None:
            total += len(node.steps)
    return round(100 * done / total) if total else 0


def actions_for(p: Project, user_id: int, role: str) -> list[dict]:
    """What this person needs to do now in this role."""
    inst = current_instance(p) if p.status == "active" else None
    if not inst:
        return []
    base = {"project_id": p.id, "project_name": p.name, "role": role, "phase_key": inst.phase.key,
            "phase_name": inst.phase.name, "instance_id": inst.id}
    if role == "author" and inst.status == "in_progress":
        return [{**base, "action": f"Complete {si.step.name}" + (" (sent back)" if si.round > 1 else ""),
                 "kind": "fill", "step_instance_id": si.id} for si in inst.steps if si.status == "in_progress"]
    if role == "approver" and inst.status == "in_progress":
        return [{**base, "action": f"Review {si.step.name}", "kind": "review", "step_instance_id": si.id}
                for si in inst.steps if si.status == "submitted"
                and user_id not in {d.user_id for d in si.decisions if d.round == si.round}]
    if role == "authorizer" and inst.status == "awaiting_signoff":
        return [{**base, "action": f"Sign off {inst.phase.name} gate review", "kind": "signoff", "step_instance_id": None}]
    return []


def latest_instances(p: Project) -> dict[int, PhaseInstance]:
    out = {}
    for i in p.instances:  # ordered by id, so the newest wins
        out[i.phase_id] = i
    return out


def project_summary(p: Project):
    return {"id": p.id, "name": p.name, "status": p.status, "workflow_id": p.workflow_id,
            "workflow_title": p.workflow.title, "created_by": user_brief(p.creator),
            "created_at": iso(p.created_at), "archived_at": iso(p.archived_at),
            "stage": stage_text(p), "progress": progress(p)}


def reference_out(r):
    return {"id": r.id, "title": r.title, "url": r.url, "note": r.note, "created_at": iso(r.created_at),
            "file": {"file_id": r.file.id, "name": r.file.original_name} if r.file else None}


def lesson_out(l):
    return {"id": l.id, "title": l.title, "body": l.body, "created_by": user_brief(l.author),
            "created_at": iso(l.created_at)}


def project_out(p: Project, user: User):
    latest = latest_instances(p)
    cur = current_instance(p)
    return {
        **project_summary(p),
        "detail_fields": p.detail_fields or [],
        "detail_values": p.detail_values or {},
        "can_manage": can_manage_project(p, user),
        "my_roles": sorted({m.role for m in p.members if m.user_id == user.id}),
        "team": [{"user": user_brief(m.user), "role": m.role,
                  "pending": [a["action"] for a in actions_for(p, m.user_id, m.role)]} for m in p.members],
        "references": [reference_out(r) for r in p.references],
        "lessons": [lesson_out(l) for l in p.lessons],
        "current_instance_id": cur.id if cur else None,
        "phases": [{
            "key": ph.key, "name": ph.name, "requires_gate": ph.requires_gate,
            "instance_id": latest[ph.id].id if ph.id in latest else None,
            "status": latest[ph.id].status if ph.id in latest else "not_started",
        } for ph in p.workflow.phases],
    }


def _decision_out(d):
    return {"user": user_brief(d.user), "round": d.round, "decision": d.decision,
            "comment": d.comment, "decided_at": iso(d.decided_at)}


def instance_out(inst: PhaseInstance, user: User):
    from .engine import can_decide_step, can_sign_off, is_author

    p = inst.project
    author = p.status == "active" and inst.status == "in_progress" and is_author(p, user)
    return {
        "id": inst.id, "project_id": p.id, "project_name": p.name, "project_status": p.status,
        "phase": {"key": inst.phase.key, "name": inst.phase.name, "requires_gate": inst.phase.requires_gate},
        "status": inst.status, "round": inst.round,
        "submitted_at": iso(inst.submitted_at), "completed_at": iso(inst.completed_at),
        "steps": [{
            "id": si.id, "name": si.step.name, "status": si.status, "round": si.round,
            "fields": [field_out(f) for f in si.step.fields],
            "decisions": [_decision_out(d) for d in si.decisions],
            "can_edit": author and si.status == "in_progress",
            "can_decide": can_decide_step(si, user),
        } for si in inst.steps],
        "values": {v.field.key: v.value for v in inst.values},
        "gate_decisions": [_decision_out(d) for d in inst.decisions],
        "approvers": [user_brief(m.user) for m in p.members if m.role == "approver"],
        "authorizers": [user_brief(m.user) for m in p.members if m.role == "authorizer"],
        "is_author": is_author(p, user),
        "can_sign_off": can_sign_off(inst, user),
    }
