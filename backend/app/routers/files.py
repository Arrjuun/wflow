from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..access import can_view_project
from ..config import settings
from ..db import get_db
from ..models import FileAsset, Project, User
from ..security import get_current_user
from ..storage import storage

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", status_code=201)
async def upload(file: UploadFile, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    key = storage.new_key()
    limit = settings.max_upload_mb * 1024 * 1024
    size = 0
    with open(storage.path(key), "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                out.close()
                storage.delete(key)
                raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB")
            out.write(chunk)
    asset = FileAsset(original_name=(file.filename or "file")[:255], storage_key=key, size=size,
                      content_type=file.content_type or "application/octet-stream", uploaded_by=user.id)
    db.add(asset)
    db.commit()
    return {"file_id": asset.id, "name": asset.original_name, "size": asset.size}


@router.get("/{file_id}")
def download(file_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = db.get(FileAsset, file_id)
    if not asset:
        raise HTTPException(404, "File not found")
    allowed = user.role == "admin" or asset.uploaded_by == user.id
    if not allowed and asset.project_id:
        project = db.get(Project, asset.project_id)
        allowed = bool(project) and can_view_project(project, user)
    if not allowed:
        raise HTTPException(403, "Not allowed")
    return FileResponse(storage.path(asset.storage_key), filename=asset.original_name,
                        media_type=asset.content_type)
