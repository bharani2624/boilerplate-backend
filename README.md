# Boilerplate Backend

FastAPI + SQLModel, backed by Supabase Postgres. Google OAuth login, JWT session auth, one demo CRUD resource (`items`).

## Stack

- FastAPI + Uvicorn/Gunicorn
- SQLModel / SQLAlchemy + psycopg2 (Supabase Postgres)
- Google OAuth (`google-auth`) for login, `python-jose` for our own session JWT

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET_KEY, GOOGLE_CLIENT_ID
uvicorn src.api.app:app --reload --port 8000
```

Tables are created automatically on startup (`SQLModel.metadata.create_all`) — no manual migration step needed for new tables. `database/migrations.py` is only for altering columns on tables that already exist in production; see the pattern there.

## Adding a new entity

1. `database/models/<name>.py` — SQLModel with `table=True`, `schema: "public"`, `to_dict()`.
2. `src/store/<name>_store.py` — extends `BaseStore`, uses `with self.get_session() as session:`.
3. `src/api/routes/<name>_routes.py` — CRUD routes, `Depends(get_current_user)` for auth.
4. Register the router in `src/api/app.py`.

## Auth flow

1. Frontend gets a Google ID token client-side (`@react-oauth/google`).
2. `POST /api/auth/google {id_token}` → backend verifies against Google, upserts `users` row, returns our own JWT.
3. Frontend sends `Authorization: Bearer <jwt>` on every request after that.
4. `GET /api/auth/me` returns the current user; any route using `Depends(get_current_user)` is protected.

This is stateless (no server-side session store), so it works the same for one user or many concurrent users — each request is authenticated independently by the JWT it carries.
