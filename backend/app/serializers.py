from .models import Project, StepInstance, User, Workflow


def iso(d):
    return d.isoformat() if d else None


def user_brief(u: User | None):
    return {"id": u.id, "name": u.name, "email": u.email} if u else None


def user_out(u: User):
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role, "status": u.status,
            "must_change_password": u.must_change_password, "created_at": iso(u.created_at)}


def workflow_summary(wf: Workflow):
    return {"id": wf.id, "title": wf.title, "description": wf.description, "status": wf.status,
            "version": wf.version, "owner": user_brief(wf.owner), "created_at": iso(wf.created_at),
            "step_count": len(wf.steps)}


def workflow_out(wf: Workflow):
    key_of = {s.id: s.key for s in wf.steps}
    return {
        **workflow_summary(wf),
        "review_comment": wf.review_comment,
        "steps": [{
            "id": s.id, "key": s.key, "name": s.name, "order": s.order, "is_start": s.is_start,
            "is_terminal": s.is_terminal, "approval_policy": s.approval_policy,
            "fields": [{"id": f.id, "key": f.key, "type": f.type, "label": f.label,
                        "required": f.required, "config": f.config or {}} for f in s.fields],
        } for s in wf.steps],
        "transitions": [{
            "from_key": key_of[t.from_step_id], "to_key": key_of[t.to_step_id],
            "condition": t.condition, "priority": t.priority, "is_default": t.is_default,
        } for t in wf.transitions],
    }


def graph_from_workflow(wf: Workflow):
    key_of = {s.id: s.key for s in wf.steps}
    steps = [{"key": s.key, "name": s.name, "is_start": s.is_start, "is_terminal": s.is_terminal,
              "fields": [{"key": f.key, "label": f.label} for f in s.fields]} for s in wf.steps]
    transitions = [{"from_key": key_of[t.from_step_id], "to_key": key_of[t.to_step_id],
                    "condition": t.condition, "is_default": t.is_default} for t in wf.transitions]
    return steps, transitions


def instance_brief(inst: StepInstance):
    return {"id": inst.id, "project_id": inst.project_id, "project_name": inst.project.name,
            "step_key": inst.step.key, "step_name": inst.step.name, "status": inst.status,
            "round": inst.round, "assignee": user_brief(inst.assignee),
            "submitted_at": iso(inst.submitted_at), "completed_at": iso(inst.completed_at)}


def instance_out(inst: StepInstance, user: User):
    approvals = [{"user": user_brief(a.user), "round": a.round, "decision": a.decision,
                  "comment": a.comment, "decided_at": iso(a.decided_at)} for a in inst.approvals]
    pending_mine = any(a.user_id == user.id and a.round == inst.round and a.decision == "pending"
                       for a in inst.approvals)
    return {
        **instance_brief(inst),
        "project_status": inst.project.status,
        "approval_policy": inst.step.approval_policy,
        "fields": [{"id": f.id, "key": f.key, "type": f.type, "label": f.label,
                    "required": f.required, "config": f.config or {}} for f in inst.step.fields],
        "values": {v.field.key: v.value for v in inst.values},
        "approvals": approvals,
        "can_edit": inst.status == "in_progress" and (inst.assignee_id == user.id or user.role == "admin"),
        "can_decide": inst.status == "submitted" and (pending_mine or user.role == "admin"),
    }


def project_summary(p: Project):
    open_steps = [i.step.name for i in p.instances if i.status in ("in_progress", "submitted")]
    return {"id": p.id, "name": p.name, "status": p.status, "workflow_id": p.workflow_id,
            "workflow_title": p.workflow.title, "created_by": user_brief(p.creator),
            "created_at": iso(p.created_at), "archived_at": iso(p.archived_at), "open_steps": open_steps}


def project_out(p: Project):
    approvers: dict[int, list] = {}
    for a in p.approver_assignments:
        approvers.setdefault(a.step_id, []).append(a.user_id)
    return {
        **project_summary(p),
        "instances": [instance_brief(i) for i in p.instances],
        "steps": [{"key": s.key, "name": s.name, "is_terminal": s.is_terminal} for s in p.workflow.steps],
    }
