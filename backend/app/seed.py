from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import User
from .security import hash_password


def ensure_admin(db: Session) -> None:
    if db.scalar(select(User).where(User.role == "admin")):
        return
    db.add(User(email=settings.admin_email.lower(), name=settings.admin_name, role="admin",
                status="active", hashed_password=hash_password(settings.admin_password)))
    db.commit()
