from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import engine
from ..access import can_manage_project, can_view_project
from ..db import get_db
from ..errors import EngineError
from ..models import FileAsset, Project, ProjectLesson, ProjectMember, ProjectReference, User, Workflow, now
from ..schemas import LessonIn, MemberIn, MembersIn, ProjectDetailsIn, ProjectIn, ReferenceIn
from ..security import get_current_user
from ..serializers import actions_for, lesson_out, project_out, project_summary, reference_out

router = APIRouter(tags=["projects"])


def _get(db: Session, project_id: int, user: User, manage=False) -> Project:
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    if not can_view_project(p, user):
        raise HTTPException(403, "Not allowed")
    if manage and not can_manage_project(p, user):
        raise HTTPException(403, "Only the project creator or an admin can do this")
    return p


def _visible(user: User):
    q = select(Project)
    if user.role != "admin":
        q = q.where(or_(Project.created_by == user.id,
                        Project.id.in_(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id))))
    return q


def _check_members(db: Session, members: list[MemberIn]) -> list[MemberIn]:
    unique = list({(m.user_id, m.role): m for m in members}.values())
    errors = []
    if not any(m.role == "author" for m in unique):
        errors.append("Add at least one author")
    ids = {m.user_id for m in unique}
    active = set(db.scalars(select(User.id).where(User.id.in_(ids), User.status == "active")))
    if ids - active:
        errors.append("Every team member must be an active user")
    if errors:
        raise EngineError(422, errors)
    return unique


@router.get("/projects")
def list_projects(archived: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = _visible(user).order_by(Project.created_at.desc())
    q = q.where(Project.status == "archived") if archived else q.where(Project.status != "archived")
    return [project_summary(p) for p in db.scalars(q)]


@router.get("/me/actions")
def my_actions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Everything waiting on the current user, across projects."""
    q = select(Project).where(Project.status == "active",
                              Project.id.in_(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)))
    out = []
    for p in db.scalars(q):
        for role in sorted({m.role for m in p.members if m.user_id == user.id}):
            out.extend(actions_for(p, user.id, role))
    return out


def _apply_details(db: Session, p: Project, body: ProjectDetailsIn):
    fields, values = engine.clean_details(db, p, [f.model_dump() for f in body.detail_fields], body.detail_values)
    p.name, p.detail_fields, p.detail_values = body.name.strip(), fields, values


@router.post("/projects", status_code=201)
def create_project(body: ProjectIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wf = db.get(Workflow, body.workflow_id)
    if not wf or wf.status != "approved":
        raise HTTPException(400, "Projects can only be created from approved workflows")
    members = _check_members(db, body.members)
    p = Project(workflow_id=wf.id, name=body.name.strip(), created_by=user.id)
    db.add(p)
    db.flush()
    _apply_details(db, p, body)
    for m in members:
        p.members.append(ProjectMember(project_id=p.id, user_id=m.user_id, role=m.role))
    db.flush()
    engine.start_project(db, p)
    engine.audit(db, user, "project.created", "project", p.id)
    db.commit()
    return project_out(p, user)


@router.get("/projects/{project_id}")
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return project_out(_get(db, project_id, user), user)


@router.patch("/projects/{project_id}")
def update_details(project_id: int, body: ProjectDetailsIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = _get(db, project_id, user, manage=True)
    if p.status == "archived":
        raise HTTPException(409, "Archived projects cannot be changed")
    _apply_details(db, p, body)
    engine.audit(db, user, "project.updated", "project", p.id)
    db.commit()
    return project_out(p, user)


@router.put("/projects/{project_id}/members")
def set_members(project_id: int, body: MembersIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Replace the team. Approvers/authorizers can be added or removed at any time; an open
    gate review is re-checked against the new team."""
    p = _get(db, project_id, user, manage=True)
    if p.status == "archived":
        raise HTTPException(409, "Archived projects cannot be changed")
    members = _check_members(db, body.members)
    p.members.clear()
    db.flush()
    for m in members:
        p.members.append(ProjectMember(project_id=p.id, user_id=m.user_id, role=m.role))
    db.flush()
    engine.reevaluate(db, p)
    engine.audit(db, user, "project.team_changed", "project", p.id, {"members": [m.model_dump() for m in members]})
    db.commit()
    return project_out(p, user)


@router.post("/projects/{project_id}/references", status_code=201)
def add_reference(project_id: int, body: ReferenceIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    p = _get(db, project_id, user, manage=True)
    url = body.url.strip()
    if not url and not body.file_id:
        raise EngineError(422, ["Add a link or a file"])
    if url:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise EngineError(422, ["The link must be a full http(s) URL"])
    if body.file_id:
        asset = db.get(FileAsset, body.file_id)
        if not asset:
            raise EngineError(422, ["File not found"])
        asset.project_id = p.id
    ref = ProjectReference(project_id=p.id, title=body.title.strip(), url=url, file_id=body.file_id,
                           note=body.note.strip(), created_by=user.id)
    p.references.append(ref)
    db.commit()
    return reference_out(ref)


@router.delete("/projects/{project_id}/references/{ref_id}", status_code=204)
def delete_reference(project_id: int, ref_id: int, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    p = _get(db, project_id, user, manage=True)
    ref = next((r for r in p.references if r.id == ref_id), None)
    if not ref:
        raise HTTPException(404, "Reference not found")
    p.references.remove(ref)
    db.commit()


@router.post("/projects/{project_id}/lessons", status_code=201)
def add_lesson(project_id: int, body: LessonIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Lessons learned: added by the project creator (or an admin), at any time, including after completion."""
    p = _get(db, project_id, user, manage=True)
    lesson = ProjectLesson(project_id=p.id, title=body.title.strip(), body=body.body.strip(), created_by=user.id)
    p.lessons.append(lesson)
    db.commit()
    return lesson_out(lesson)


@router.delete("/projects/{project_id}/lessons/{lesson_id}", status_code=204)
def delete_lesson(project_id: int, lesson_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _get(db, project_id, user, manage=True)
    lesson = next((l for l in p.lessons if l.id == lesson_id), None)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    p.lessons.remove(lesson)
    db.commit()


@router.post("/projects/{project_id}/archive")
def archive(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _get(db, project_id, user, manage=True)
    if p.status != "completed":
        raise HTTPException(409, "Only completed projects can be archived")
    p.status, p.archived_at = "archived", now()
    engine.audit(db, user, "project.archived", "project", p.id)
    db.commit()
    return project_out(p, user)


@router.post("/projects/{project_id}/unarchive")
def unarchive(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _get(db, project_id, user, manage=True)
    if p.status != "archived":
        raise HTTPException(409, "Project is not archived")
    p.status, p.archived_at = "completed", None
    engine.audit(db, user, "project.unarchived", "project", p.id)
    db.commit()
    return project_out(p, user)
