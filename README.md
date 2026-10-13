# CAF

FastAPI + SQLAlchemy (SQLite first, PostgreSQL later) + React (Redux Toolkit / thunks), served by FastAPI.

## Run it (development)

Backend (terminal 1):

    cd backend
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload          # http://localhost:8000/docs

The first start creates the tables (AUTO_CREATE_TABLES=true) and an admin user from ADMIN_EMAIL / ADMIN_PASSWORD.

Frontend (terminal 2):

    cd frontend
    npm install
    npm run dev                            # http://localhost:5173 (proxies /api to :8000)

## Run it as one app (FastAPI serves React)

    cd frontend && npm install && npm run build     # writes into backend/app/static
    cd ../backend && uvicorn app.main:app           # http://localhost:8000

## How it is organised

- **Workflow** → **phases** → **steps** (tabs) → **fields**, all built in the Workflows screen. Add, rename, reorder or
  remove phases and steps freely; an admin approves the workflow before projects can use it.
- **Paths** connect phases. A single path is always taken. For a branch, give one path a condition and mark the other
  default: the condition is checked first, the default is taken otherwise.
- **Project team** (chosen by the project creator, editable any time):
  - **Authors** (the project team) fill in and submit steps. The creator cannot unless added as an author.
  - **Admins can do everything** on any project: fill and submit steps, approve steps and sign off phases (an admin's approval or sign-off is final), and manage details, team and references.
  - **Approvers** approve every submitted step; all of them must approve. A rejection sends the step back with a comment.
  - **Authorizers** sign off a phase once all its steps are approved (any one). A sign-off rejection sends the whole phase back.
  - With no approvers, steps are approved on submission. With no authorizers, or "Gate review" unticked, a phase completes when its steps are approved.
- **Project details** are fields the project creator defines per project (for example FEM registration number, start date),
  using the same field types as steps. Only the project name is built in.
- **References** and **Lessons learned**: added by the project creator (or an admin) on the project dashboard, any time, even after completion. Neither is part of any approval.
- Field types: short text, long text, drop-down, date, URL, number, file, table (repeating rows), section heading.

Two optional example workflows, an M&S certification and a branching Change Request (you can delete `app/seed_example.py`). Running it again skips workflows that already exist:

    cd backend && python -m app.seed_example

After pulling this version, delete `backend/app.db` once: the tables changed.

## Tests

    cd backend && pytest

## Move to PostgreSQL

1. Start Postgres (`docker compose up db`), set `DATABASE_URL=postgresql+psycopg://workflow:workflow@localhost:5432/workflow` and `AUTO_CREATE_TABLES=false`.
2. `alembic revision --autogenerate -m "initial"` then `alembic upgrade head` (run once; commit the revision).
3. Start the app. Nothing else changes: JSON columns become JSONB automatically.

Full stack in containers: `docker compose up --build` (needs the initial Alembic revision from step 2 committed first).

## Layout

    backend/app/models.py       tables          engine.py     submit / approve / branch logic
    backend/app/conditions.py   conditions + graph validation (pure, unit-tested)
    backend/app/fields.py       field type registry (add new types here)
    backend/app/routers/        API under /api/v1
    frontend/src/slices/        Redux slices with createAsyncThunk
    frontend/src/fields/        frontend field registry (add new types here)
    frontend/src/pages/         screens

## Add a new field type (e.g. "checkbox")

1. backend/app/fields.py: subclass `FieldType`, set `name`/`label`, implement `clean_value`, decorate with `@register`.
2. frontend/src/fields/registry.jsx: add an entry with `label`, `Editor`, `Viewer`.
No migration needed.

## What happens when everything is complete

1. When every step of a phase is approved, the phase goes to **awaiting sign-off** if the project has authorizers (and the phase has "Gate review" ticked). Otherwise it moves on straight away.
2. An authorizer (or an admin) signs off; the project then follows the path out of that phase: the matching condition, or the default.
3. When the **end phase** is signed off, the project becomes **Completed** (100%) and everything is read-only.
4. The creator (or an admin) can **Archive** it; archived projects move to the "Show archived" list and can be restored.
Nothing is archived automatically. Lessons learned and references can still be added after completion.
