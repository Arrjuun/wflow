from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import engine
from ..access import can_view_instance
from ..db import get_db
from ..models import Project, StepApproval, StepInstance, User
from ..schemas import DecisionIn, ValuesIn
from ..security import get_current_user
from ..serializers import instance_brief, instance_out

router = APIRouter(tags=["tasks"])


def _get(db: Session, inst_id: int, user: User) -> StepInstance:
    inst = db.get(StepInstance, inst_id)
    if not inst:
        raise HTTPException(404, "Step not found")
    if not can_view_instance(inst, user):
        raise HTTPException(403, "Not allowed")
    return inst


@router.get("/tasks/mine")
def my_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(StepInstance).where(StepInstance.assignee_id == user.id, StepInstance.status == "in_progress"
                                   ).order_by(StepInstance.created_at)
    return [instance_brief(i) for i in db.scalars(q)]


@router.get("/approvals/mine")
def my_approvals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = (select(StepInstance).join(StepApproval, StepApproval.instance_id == StepInstance.id)
         .where(StepApproval.user_id == user.id, StepApproval.decision == "pending",
                StepApproval.round == StepInstance.round, StepInstance.status == "submitted")
         .order_by(StepInstance.submitted_at))
    return [instance_brief(i) for i in db.scalars(q)]


@router.get("/step-instances/{inst_id}")
def get_instance(inst_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return instance_out(_get(db, inst_id, user), user)


@router.put("/step-instances/{inst_id}/values")
def save_values(inst_id: int, body: ValuesIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inst = _get(db, inst_id, user)
    engine.save_draft(db, inst, user, body.values)
    db.commit()
    return instance_out(inst, user)


@router.post("/step-instances/{inst_id}/submit")
def submit(inst_id: int, body: ValuesIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inst = _get(db, inst_id, user)
    engine.submit(db, inst, user, body.values)
    db.commit()
    return instance_out(inst, user)


@router.post("/step-instances/{inst_id}/decision")
def decide(inst_id: int, body: DecisionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inst = _get(db, inst_id, user)
    engine.decide(db, inst, user, body.decision, body.comment)
    db.commit()
    return instance_out(inst, user)
