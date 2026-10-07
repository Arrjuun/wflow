# Workflow Desk

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
