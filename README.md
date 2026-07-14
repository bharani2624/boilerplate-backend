# Boilerplate Backend

FastAPI + SQLModel, backed by Supabase Postgres. Fully async (routes, stores, database
driver), Google OAuth login, JWT session auth, one demo CRUD resource (`items`), and a
fire-and-forget background-tasks pattern.

## Stack

- FastAPI + Uvicorn/Gunicorn — every route is `async def`
- SQLModel / SQLAlchemy (async ORM) + psycopg3 (native asyncio Postgres driver) against Supabase Postgres
- Google OAuth (`google-auth`) for login, `python-jose` for our own session JWT
- FastAPI's built-in `BackgroundTasks` for fire-and-forget work (not a job queue — see AGENTS.md)

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET_KEY, GOOGLE_CLIENT_ID
uvicorn src.api.app:app --reload --port 8000
```

Tables are created automatically on startup (`SQLModel.metadata.create_all`, run via
`conn.run_sync(...)` against the async engine) — no manual migration step needed for
new tables. `database/migrations.py` is only for altering columns on tables that
already exist in production; see the pattern there.

## Adding a new entity

1. `database/models/<name>.py` — SQLModel with `table=True`, `schema: "public"`, `to_dict()`.
2. `src/store/<name>_store.py` — extends `BaseStore`, every method `async def`, uses `async with self.get_session() as session:`.
3. `src/api/routes/<name>_routes.py` — CRUD routes, every handler `async def`, `Depends(get_current_user)` for auth. Add a `background_tasks: BackgroundTasks` parameter if a write should trigger non-critical follow-up work (see `src/services/background_tasks.py`).
4. Register the router in `src/api/app.py`.

See `AGENTS.md` for the full mechanical walkthrough of how a request flows through these layers.

## Auth flow

1. Frontend gets a Google ID token client-side (`@react-oauth/google`).
2. `POST /api/auth/google {id_token}` → backend verifies against Google (off the event loop, via `asyncio.to_thread`, since `google-auth`'s check is a blocking call), upserts `users` row, returns our own JWT.
3. Frontend sends `Authorization: Bearer <jwt>` on every request after that.
4. `GET /api/auth/me` returns the current user; any route using `Depends(get_current_user)` is protected.

This is stateless (no server-side session store), so it works the same for one user or many concurrent users — each request is authenticated independently by the JWT it carries.

## Background tasks

`src/services/background_tasks.py` has example fire-and-forget functions
(`log_login_event`, `log_item_created`), wired up in `auth_routes.py` and
`items_routes.py` via FastAPI's `BackgroundTasks`. They run after the response is sent,
in-process — not a durable job queue (no persistence, no retry across restarts). Fine
for logging/notifications; reach for Celery/RQ/arq + Redis if a task genuinely needs to
survive a restart or retry on failure.
