from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import ChangePasswordIn, LoginIn, RegisterIn
from ..security import (COOKIE, create_token, get_session_user, hash_password, verify_password)
from ..serializers import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    db.add(User(email=email, name=body.name.strip(), hashed_password=hash_password(body.password),
                role="user", status="pending"))
    db.commit()
    return {"message": "Account created. An admin must approve it before you can sign in."}


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower().strip()))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    if user.status == "pending":
        raise HTTPException(403, "Your account is waiting for admin approval")
    if user.status != "active":
        raise HTTPException(403, "Your account is disabled")
    response.set_cookie(COOKIE, create_token(user.id), httponly=True, samesite="lax",
                        secure=settings.cookie_secure, max_age=settings.access_token_minutes * 60)
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE)


@router.get("/me")
def me(user: User = Depends(get_session_user)):
    return user_out(user)


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: User = Depends(get_session_user),
                    db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(400, "Current password is incorrect")
    user.hashed_password = hash_password(body.new_password)
    user.must_change_password = False
    db.commit()
    return user_out(user)
