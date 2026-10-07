from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..conditions import validate_graph
from ..engine import audit
from ..errors import EngineError
from ..fields import FieldError, get_type, list_types
from ..models import Project, StepField, StepTransition, User, Workflow, WorkflowStep, now
from ..schemas import ReviewIn, WorkflowCreate, WorkflowIn
from ..security import get_current_user, require_admin
from ..serializers import graph_from_workflow, workflow_out, workflow_summary

router = APIRouter(tags=["workflows"])
EDITABLE = ("draft", "rejected")


def _get(db: Session, wf_id: int) -> Workflow:
    wf = db.get(Workflow, wf_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf


def _can_view(wf: Workflow, user: User) -> bool:
    return user.role == "admin" or wf.created_by == user.id or wf.status == "approved"


def _owner_or_admin(wf: Workflow, user: User):
    if user.role != "admin" and wf.created_by != user.id:
        raise HTTPException(403, "Only the workflow owner or an admin can do this")


def apply_graph(db: Session, wf: Workflow, data: WorkflowIn) -> None:
    keys = [s.key.strip() for s in data.steps]
    if len(set(keys)) != len(keys):
        raise EngineError(422, ["Step keys must be unique"])
    for s in data.steps:
        fkeys = [f.key.strip() for f in s.fields]
        if len(set(fkeys)) != len(fkeys):
            raise EngineError(422, [f"Step {s.key}: field keys must be unique"])
    wf.title, wf.description = data.title.strip(), data.description
    wf.transitions.clear()
    db.flush()
    wf.steps.clear()
    db.flush()
    by_key = {}
    for i, s in enumerate(data.steps):
        step = WorkflowStep(key=s.key.strip(), name=s.name.strip() or s.key.strip(), order=i,
                            is_start=s.is_start, is_terminal=s.is_terminal, approval_policy=s.approval_policy)
        for j, f in enumerate(s.fields):
            try:
                config = get_type(f.type).validate_config(f.config)
            except (FieldError, ValueError, TypeError) as e:
                raise EngineError(422, [f"Step {s.key}, field '{f.label or f.key}': {e}"])
            step.fields.append(StepField(key=f.key.strip(), type=f.type, label=f.label.strip() or f.key.strip(),
                                         required=f.required, config=config, order=j))
        wf.steps.append(step)
        by_key[step.key] = step
    db.flush()
    for t in data.transitions:
        a, b = by_key.get(t.from_key), by_key.get(t.to_key)
        if not a or not b:
            raise EngineError(422, ["A transition points to a step that does not exist"])
        wf.transitions.append(StepTransition(from_step_id=a.id, to_step_id=b.id, condition=t.condition or None,
                                             priority=t.priority, is_default=t.is_default))
    db.flush()


def _validate_or_422(wf: Workflow):
    errors = validate_graph(*graph_from_workflow(wf))
    if errors:
        raise HTTPException(422, {"errors": errors})


@router.get("/field-types")
def field_types(_: User = Depends(get_current_user)):
    return list_types()


@router.get("/workflows")
def list_workflows(scope: str = "visible", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """scope: visible (mine + approved; admin sees all) | mine | approved"""
    q = select(Workflow).order_by(Workflow.created_at.desc())
    if scope == "mine":
        q = q.where(Workflow.created_by == user.id)
    elif scope == "approved":
        q = q.where(Workflow.status == "approved")
    elif user.role != "admin":
        q = q.where(or_(Workflow.created_by == user.id, Workflow.status == "approved"))
    return [workflow_summary(w) for w in db.scalars(q)]


@router.post("/workflows", status_code=201)
def create_workflow(body: WorkflowCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wf = Workflow(title=body.title.strip(), description=body.description, created_by=user.id)
    db.add(wf)
    db.flush()
    audit(db, user, "workflow.created", "workflow", wf.id)
    db.commit()
    return workflow_out(wf)


@router.get("/workflows/{wf_id}")
def get_workflow(wf_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wf = _get(db, wf_id)
    if not _can_view(wf, user):
        raise HTTPException(403, "Not allowed")
    return workflow_out(wf)


@router.put("/workflows/{wf_id}")
def save_workflow(wf_id: int, body: WorkflowIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    wf = _get(db, wf_id)
    _owner_or_admin(wf, user)
    if wf.status not in EDITABLE:
        raise HTTPException(409, "Only draft or rejected workflows can be edited. Clone it to make changes.")
    apply_graph(db, wf, body)
    audit(db, user, "workflow.saved", "workflow", wf.id)
    db.commit()
    return workflow_out(wf)


@router.delete("/workflows/{wf_id}", status_code=204)
def delete_workflow(wf_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wf = _get(db, wf_id)
    _owner_or_admin(wf, user)
    if wf.status not in EDITABLE:
        raise HTTPException(409, "Only draft or rejected workflows can be deleted")
    db.delete(wf)
    db.commit()


@router.post("/workflows/{wf_id}/submit")
def submit_workflow(wf_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wf = _get(db, wf_id)
    _owner_or_admin(wf, user)
    if wf.status not in EDITABLE:
        raise HTTPException(409, "Workflow is not editable")
    _validate_or_422(wf)
    wf.status, wf.review_comment = "pending_approval", None
    audit(db, user, "workflow.submitted", "workflow", wf.id)
    db.commit()
    return workflow_out(wf)


@router.post("/workflows/{wf_id}/approve")
def approve_workflow(wf_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    wf = _get(db, wf_id)
    if wf.status not in ("pending_approval", "draft", "rejected"):
        raise HTTPException(409, f"Cannot approve a workflow that is {wf.status}")
    _validate_or_422(wf)
    wf.status, wf.approved_by, wf.approved_at, wf.review_comment = "approved", admin.id, now(), None
    audit(db, admin, "workflow.approved", "workflow", wf.id)
    db.commit()
    return workflow_out(wf)


@router.post("/workflows/{wf_id}/reject")
def reject_workflow(wf_id: int, body: ReviewIn, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    wf = _get(db, wf_id)
    if wf.status != "pending_approval":
        raise HTTPException(409, "Only workflows pending approval can be rejected")
    if not body.comment.strip():
        raise HTTPException(422, {"errors": ["Add a comment explaining what to change"]})
    wf.status, wf.review_comment = "rejected", body.comment.strip()
    audit(db, admin, "workflow.rejected", "workflow", wf.id)
    db.commit()
    return workflow_out(wf)


@router.post("/workflows/{wf_id}/retire")
def retire_workflow(wf_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    wf = _get(db, wf_id)
    if wf.status != "approved":
        raise HTTPException(409, "Only approved workflows can be retired")
    wf.status = "retired"
    audit(db, admin, "workflow.retired", "workflow", wf.id)
    db.commit()
    return workflow_out(wf)


@router.post("/workflows/{wf_id}/clone", status_code=201)
def clone_workflow(wf_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    src = _get(db, wf_id)
    if not _can_view(src, user):
        raise HTTPException(403, "Not allowed")
    data = workflow_out(src)
    copy = Workflow(title=src.title, description=src.description, created_by=user.id, version=src.version + 1)
    db.add(copy)
    db.flush()
    apply_graph(db, copy, WorkflowIn(title=data["title"], description=data["description"],
                                     steps=data["steps"], transitions=data["transitions"]))
    audit(db, user, "workflow.cloned", "workflow", copy.id, {"from": src.id})
    db.commit()
    return workflow_out(copy)
