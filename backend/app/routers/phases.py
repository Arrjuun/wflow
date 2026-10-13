from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import engine
from ..access import can_view_project
from ..db import get_db
from ..models import PhaseInstance, StepInstance, User
from ..schemas import DecisionIn, ValuesIn
from ..security import get_current_user
from ..serializers import instance_out

router = APIRouter(tags=["phases"])


def _phase(db: Session, inst_id: int, user: User) -> PhaseInstance:
    inst = db.get(PhaseInstance, inst_id)
    if not inst:
        raise HTTPException(404, "Phase not found")
    if not can_view_project(inst.project, user):
        raise HTTPException(403, "Not allowed")
    return inst


def _step(db: Session, step_id: int, user: User) -> StepInstance:
    si = db.get(StepInstance, step_id)
    if not si:
        raise HTTPException(404, "Step not found")
    if not can_view_project(si.phase_instance.project, user):
        raise HTTPException(403, "Not allowed")
    return si


@router.get("/phase-instances/{inst_id}")
def get_phase(inst_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return instance_out(_phase(db, inst_id, user), user)


@router.put("/phase-instances/{inst_id}/values")
def save_values(inst_id: int, body: ValuesIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save a draft of the phase's open steps (project authors only)."""
    inst = _phase(db, inst_id, user)
    engine.save_values(db, inst, user, body.values)
    db.commit()
    return instance_out(inst, user)


@router.post("/step-instances/{step_id}/submit")
def submit_step(step_id: int, body: ValuesIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    si = _step(db, step_id, user)
    engine.submit_step(db, si, user, body.values)
    db.commit()
    return instance_out(si.phase_instance, user)


@router.post("/step-instances/{step_id}/decision")
def decide_step(step_id: int, body: DecisionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    si = _step(db, step_id, user)
    engine.decide_step(db, si, user, body.decision, body.comment)
    db.commit()
    return instance_out(si.phase_instance, user)


@router.post("/phase-instances/{inst_id}/signoff")
def sign_off(inst_id: int, body: DecisionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inst = _phase(db, inst_id, user)
    engine.sign_off(db, inst, user, body.decision, body.comment)
    db.commit()
    return instance_out(inst, user)
