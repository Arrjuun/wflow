import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..engine import audit
from ..models import User
from ..schemas import UserPatch
from ..security import get_current_user, hash_password, require_admin
from ..serializers import user_brief, user_out

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/directory")
def directory(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Active users, for assignee/approver pickers."""
    users = db.scalars(select(User).where(User.status == "active").order_by(User.name)).all()
    return [user_brief(u) for u in users]


@router.get("")
def list_users(status: str | None = None, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    q = select(User).order_by(User.created_at.desc())
    if status:
        q = q.where(User.status == status)
    return [user_out(u) for u in db.scalars(q)]


def _get(db, user_id) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.post("/{user_id}/approve")
def approve(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get(db, user_id)
    if user.status != "pending":
        raise HTTPException(400, "User is not pending")
    user.status = "active"
    audit(db, admin, "user.approved", "user", user.id)
    db.commit()
    return user_out(user)


@router.patch("/{user_id}")
def patch(user_id: int, body: UserPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get(db, user_id)
    if user.id == admin.id and (body.status == "disabled" or body.role == "user"):
        raise HTTPException(400, "You cannot demote or disable yourself")
    if body.status:
        user.status = body.status
    if body.role:
        user.role = body.role
    audit(db, admin, "user.updated", "user", user.id, body.model_dump(exclude_none=True))
    db.commit()
    return user_out(user)


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get(db, user_id)
    temp = secrets.token_urlsafe(9)
    user.hashed_password = hash_password(temp)
    user.must_change_password = True
    audit(db, admin, "user.password_reset", "user", user.id)
    db.commit()
    return {"temporary_password": temp}
