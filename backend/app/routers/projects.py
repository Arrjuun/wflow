from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import engine
from ..access import can_view_project
from ..db import get_db
from ..errors import EngineError
from ..models import Project, ProjectApprover, ProjectAssignment, User, Workflow, now
from ..schemas import ProjectIn
from ..security import get_current_user
from ..serializers import project_out, project_summary

router = APIRouter(prefix="/projects", tags=["projects"])


def _get(db: Session, project_id: int, user: User) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    if not can_view_project(p, user):
        raise HTTPException(403, "Not allowed")
    return p


@router.get("")
def list_projects(archived: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Project).order_by(Project.created_at.desc())
    q = q.where(Project.status == "archived") if archived else q.where(Project.status != "archived")
    if user.role != "admin":
        q = q.where(or_(
            Project.created_by == user.id,
            Project.id.in_(select(ProjectAssignment.project_id).where(ProjectAssignment.assignee_id == user.id)),
            Project.id.in_(select(ProjectApprover.project_id).where(ProjectApprover.user_id == user.id)),
        ))
    return [project_summary(p) for p in db.scalars(q)]


@router.post("", status_code=201)
def create_project(body: ProjectIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wf = db.get(Workflow, body.workflow_id)
    if not wf or wf.status != "approved":
        raise HTTPException(400, "Projects can only be created from approved workflows")
    steps = {s.key: s for s in wf.steps}
    errors = []
    for key in steps:
        if key not in body.assignments:
            errors.append(f"Step {key} ({steps[key].name}) needs an assignee")
    for key in {*body.assignments, *body.approvers}:
        if key not in steps:
            errors.append(f"Unknown step '{key}'")
    user_ids = set(body.assignments.values()) | {u for ids in body.approvers.values() for u in ids}
    active = {u.id for u in db.scalars(select(User).where(User.id.in_(user_ids), User.status == "active"))}
    if user_ids - active:
        errors.append("Every assignee and approver must be an active user")
    if errors:
        raise EngineError(422, errors)

    project = Project(workflow_id=wf.id, name=body.name.strip(), created_by=user.id)
    db.add(project)
    db.flush()
    for key, uid in body.assignments.items():
        project.assignments.append(ProjectAssignment(project_id=project.id, step_id=steps[key].id, assignee_id=uid))
    for key, uids in body.approvers.items():
        for uid in dict.fromkeys(uids):
            project.approver_assignments.append(
                ProjectApprover(project_id=project.id, step_id=steps[key].id, user_id=uid))
    db.flush()
    engine.start_project(db, project)
    engine.audit(db, user, "project.created", "project", project.id)
    db.commit()
    return project_out(project)


@router.get("/{project_id}")
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return project_out(_get(db, project_id, user))


def _creator_or_admin(p: Project, user: User):
    if user.role != "admin" and p.created_by != user.id:
        raise HTTPException(403, "Only the project creator or an admin can do this")


@router.post("/{project_id}/archive")
def archive(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _get(db, project_id, user)
    _creator_or_admin(p, user)
    if p.status != "completed":
        raise HTTPException(409, "Only completed projects can be archived")
    p.status, p.archived_at = "archived", now()
    engine.audit(db, user, "project.archived", "project", p.id)
    db.commit()
    return project_out(p)


@router.post("/{project_id}/unarchive")
def unarchive(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _get(db, project_id, user)
    _creator_or_admin(p, user)
    if p.status != "archived":
        raise HTTPException(409, "Project is not archived")
    p.status, p.archived_at = "completed", None
    engine.audit(db, user, "project.unarchived", "project", p.id)
    db.commit()
    return project_out(p)
