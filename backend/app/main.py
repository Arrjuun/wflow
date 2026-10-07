import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .db import Base, SessionLocal, engine
from .errors import EngineError
from .routers import auth, files, projects, tasks, users, workflows
from .seed import ensure_admin

BASE = Path(__file__).parent
STATIC = BASE / "static"
templates = Jinja2Templates(directory=BASE / "templates")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:  # development convenience; use Alembic in production
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_admin(db)
    yield


app = FastAPI(title="Workflow Approval", lifespan=lifespan)


@app.exception_handler(EngineError)
async def engine_error_handler(_: Request, exc: EngineError):
    detail = {"errors": exc.message} if isinstance(exc.message, list) else exc.message
    return JSONResponse({"detail": detail}, status_code=exc.status)


for r in (auth, users, workflows, projects, tasks, files):
    app.include_router(r.router, prefix="/api/v1")

if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _assets() -> dict | None:
    for path in (STATIC / ".vite" / "manifest.json", STATIC / "manifest.json"):
        if path.exists():
            manifest = json.loads(path.read_text())
            entry = manifest.get("index.html") or next(v for v in manifest.values() if v.get("isEntry"))
            return {"js": "/static/" + entry["file"], "css": ["/static/" + c for c in entry.get("css", [])]}
    return None


@app.get("/{full_path:path}", include_in_schema=False)
def spa(request: Request, full_path: str):
    """Serve the React app for every non-API route so client-side routing works."""
    if full_path.startswith("api/"):
        raise HTTPException(404, "Not found")
    assets = _assets()
    if not assets:
        return HTMLResponse("Frontend not built yet. Run `npm run build` in /frontend.", status_code=503)
    return templates.TemplateResponse(request, "index.html", {"assets": assets})
