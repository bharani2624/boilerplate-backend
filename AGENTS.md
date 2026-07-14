# Backend — Agent Instructions

FastAPI + SQLModel service, single Postgres database (Supabase), Google OAuth login with
stateless JWT sessions. Read this before editing — it tells you where things live and
the pattern to follow so new code stays consistent with existing code.

## Stack

- FastAPI (routing), Uvicorn/Gunicorn (server)
- SQLModel / SQLAlchemy 2.x + psycopg3 (Postgres driver) — one shared `engine` (`database/session.py`)
- `python-jose` for JWT, `google-auth` for verifying Google ID tokens
- pydantic-settings for env config (`config/settings.py`)

No multi-tenancy, no ORM migration tool (Alembic) — this is intentionally minimal. Tables
are created automatically from SQLModel classes on startup.

## System design overview (bird's-eye view)

```
 Browser                Google                 Render (backend)              Supabase
┌────────┐   OAuth    ┌────────┐   verify id_token ┌──────────────────┐  psycopg  ┌──────────┐
│ Next.js│──────────▶│ Google  │──────────────────▶│ FastAPI (gunicorn │──────────▶│ Postgres │
│ (Render│◀───JWT─────│ Identity│                    │  -w 2, thread pool│           │ (single  │
│ or     │  in every   └────────┘                    │  per worker)      │           │  DB, no  │
│ Vercel)│  request                                   └──────────────────┘           │  replica)│
└────────┘                                                                            └──────────┘
```

- **One database, one region, no read replicas, no cache layer (no Redis).** Every read
  and write goes straight to the same Supabase Postgres instance. This is a deliberate
  simplification for a hackathon boilerplate — it means the database is the one real
  single point of failure and the one real scaling ceiling. If a problem statement
  needs to survive real load (thousands of req/s, heavy read traffic), the first thing
  to add is a read-through cache (Redis) in front of hot GETs, not more backend
  instances — more backend instances just means more connections competing for the
  same Postgres pooler slots.
- **The backend itself is stateless and horizontally scalable as-is.** Because auth is
  a JWT decode with no server-side session (see "Concurrency" above), you can point a
  load balancer at N identical backend instances with zero sticky-session config —
  any instance can answer any authenticated user's request. Render's own autoscaling
  (paid tiers) or manually bumping instance count works with no code changes. The
  constraint that *does* need attention when scaling out is Postgres's connection
  limit — each instance opens its own pool (`pool_size + max_overflow`), so N instances
  means N× that many connections against Supabase's pooler, which is finite.
- **Frontend and backend are two independently deployed services, not one monolith.**
  They only ever talk over HTTP (`NEXT_PUBLIC_API_URL`) — the frontend has no direct
  database access and no server secrets beyond a public Google client id. This means
  they scale, deploy, and fail independently: the frontend going down doesn't take the
  API down and vice versa, and you can redeploy one without redeploying the other.
- **Trust boundary is the JWT signing key, full stop.** `JWT_SECRET_KEY` is the only
  secret that, if leaked, lets someone mint a valid session for any user id without
  ever going through Google. Google's OAuth is only trusted once, at login, to answer
  "is this really this person" — after that, our own signature is the only thing any
  route checks. This is why `.env` is gitignored and why the deploy instructions don't
  put that key anywhere client-visible.
- **No background job system.** Everything happens synchronously inside a request
  (including the Google token verification network call in `/api/auth/google`). Fine
  at this scale; if a builder-round problem statement needs something slow (sending
  emails, processing uploads, calling a slow third-party API), that's the point where
  you'd introduce a queue (e.g. a simple background task or a worker process) rather
  than making the request wait on it — don't build that ahead of time, only add it if
  the actual problem statement needs it.

## Where things live

```
config/settings.py              — all env config, one Settings object imported everywhere as `from config.settings import settings`
database/session.py             — the SQLAlchemy engine + create_db_and_tables() + get_session() context manager
database/models/                — SQLModel table classes (one file per entity)
database/models/user.py         — User (Google OAuth identity)
database/models/item.py         — Item (demo CRUD entity, owned by a user) — DELETE/replace this for your real domain model
database/migrations.py          — manual column/index ALTERs for tables that already exist in prod; new tables don't need entries here
database/migration_helpers.py   — idempotent add_column/drop_column/create_index/execute_sql helpers used by migrations.py
src/services/auth_service.py    — verify_google_id_token(), create_access_token(), decode_access_token()
src/api/middleware/auth.py      — get_current_user() FastAPI dependency; put `Depends(get_current_user)` on any route that needs auth
src/api/routes/health.py        — GET /api/health, unauthenticated
src/api/routes/auth_routes.py   — POST /api/auth/google (login), GET /api/auth/me
src/api/routes/items_routes.py  — demo CRUD (GET/POST /api/items, GET/PUT/DELETE /api/items/{id}) — copy this file's shape for new entities
src/store/base_store.py         — BaseStore.get_session() wrapper; all stores extend this
src/store/user_store.py         — DB operations for User
src/store/item_store.py         — DB operations for Item — copy this file's shape for new entities
src/api/app.py                  — FastAPI app instance, CORS, router registration, startup (create tables + run migrations)
requirements.txt                — pinned/floor-pinned deps; psycopg is version-floored (>=3.2.10) because older pins lack wheels for newer Python
Dockerfile                      — for Render/production; local dev does not need Docker (see README.md)
.env.example                    — template; copy to .env, never commit .env
```

## The CRUD pattern (follow this for every new entity)

1. **Model** — `database/models/<entity>.py`: `class X(SQLModel, table=True)`, `__tablename__`, `__table_args__ = {"schema": "public"}`, UUID PK via `Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())`, `created_at`/`updated_at` as `TIMESTAMP(timezone=True)`, a `to_dict()` method. Register it in `database/models/__init__.py`.
2. **Store** — `src/store/<entity>_store.py`: extends `BaseStore`, every method opens `with self.get_session() as session:` (commits on exit, rolls back on exception — never call `session.commit()` yourself). Call `session.flush()` + `session.refresh(obj)` before returning an object you just inserted/updated, so DB-generated fields (id, server defaults) are populated.
3. **Route** — `src/api/routes/<entity>_routes.py`: one `APIRouter()`, Pydantic request models with `Field(description=...)`, `Depends(get_current_user)` on every handler that touches user-owned data, response shape `{"status": "success", "data": ...}` (add `"count"` for list endpoints), 404 via `HTTPException(status_code=404)` — never a bare 500 for "not found."
4. **Register** — add the router in `src/api/app.py` with `app.include_router(<entity>_routes.router, prefix="/api/<entity>", tags=["<entity>"])`.
5. Table appears automatically on next server restart — no migration step needed. Only touch `database/migrations.py` when altering a column on a table that's already live in Supabase.

## How a request actually flows (routes → middleware → store → session → database)

This is the exact call chain for `GET /api/items`, top to bottom — every other route
follows the same shape:

1. **Route** (`src/api/routes/items_routes.py`) — FastAPI matches the path to
   `list_items()`. Its signature declares `current_user: dict = Depends(get_current_user)`.
   FastAPI runs the dependency *before* the function body.
2. **Middleware/auth dependency** (`src/api/middleware/auth.py`) — this is not Starlette
   `BaseHTTPMiddleware` (it doesn't wrap every request globally); it's a FastAPI
   `Depends()` function, so it only runs on routes that explicitly ask for it. It:
   - reads the raw `Authorization` header,
   - rejects with 401 if it's missing or not `Bearer <token>`,
   - calls `decode_access_token(token)` (in `src/services/auth_service.py`), which
     verifies the JWT signature against `settings.jwt_secret_key` and checks `exp`,
   - rejects with 401 if that returns `None` (bad signature, expired, malformed),
   - otherwise returns `{"user_id": payload["sub"], "email": payload["email"]}`, which
     FastAPI injects into the route as `current_user`.
   Nothing is looked up in the database at this step — the JWT payload alone is trusted
   (that's what "stateless" means here). No DB round trip, no Redis, no shared session
   state; the token itself is the entire proof of identity.
3. **Route body** — now runs with a trusted `current_user["user_id"]`, and calls
   `item_store.list_for_user(current_user["user_id"])`.
4. **Store** (`src/store/item_store.py`) — opens `with self.get_session() as session:`
   and runs a SQLModel `select(Item).where(Item.user_id == user_id)`. This is the only
   place `user_id` is used as a database filter — it's what makes one user unable to
   see another's rows, not anything in the route or middleware layer.
5. **Session** (`database/session.py`) — `get_session()` is a context manager that
   opens a `Session` on the shared `engine`, yields it, and on exit: commits if the
   `with` block succeeded, rolls back if it raised, and always closes the session
   afterward. Stores never call `session.commit()`/`.rollback()`/`.close()` themselves —
   that's centralized here so it can't be gotten wrong in any one store.
6. **Engine** (`database/session.py`, module level) — a single SQLAlchemy `Engine`
   created once at import time from `settings.database_url`, holding a connection
   pool (`pool_size`/`max_overflow` from settings) to Supabase's pooler.
   `pool_pre_ping=True` makes it test a pooled connection is alive before reusing it,
   since Supabase's pooler drops idle connections. This engine is shared by every
   store — there is one pool for the whole process, not one per request.
7. **Route returns** `{"status": "success", "data": [...], "count": N}` — FastAPI
   serializes it to JSON. The `to_dict()` on each model is what makes UUID/datetime
   fields JSON-safe.

Login (`POST /api/auth/google`) is the one route that does *not* use
`get_current_user` — it's how a client gets a JWT in the first place, so requiring one
would be circular. Everything downstream of login uses the flow above.

## Auth (how a request gets identified) — summary

Stateless — no session store, no Redis, no cookies. `Authorization: Bearer <jwt>` on every
authenticated request. `get_current_user` (in `src/api/middleware/auth.py`) decodes the JWT
and returns `{"user_id": ..., "email": ...}`; use `current_user["user_id"]` to scope queries
to the caller (see `item_store.py` — every method takes `user_id` and filters/checks by it).

To add a new protected route: add `current_user: dict = Depends(get_current_user)` as a
parameter and use `current_user["user_id"]`. See the step-by-step flow above for what
happens mechanically when that dependency runs.

## Database & session lifecycle (mental model)

There are three layers, and it matters which one you touch when:

- **Engine** (`database/session.py`, `engine = create_engine(...)`) — created once per
  process. Holds the connection pool. You never touch this directly outside of
  `database/session.py` and `database/migrations.py` (which needs raw `engine` access
  for ALTER TABLE statements — see `database/migration_helpers.py`).
- **Session** (`get_session()`) — created once per store method call, short-lived,
  scoped to a single `with` block. This is what you use in every store method:
  `with self.get_session() as session: ...`. Never hold a session across two separate
  method calls or requests.
- **Tables** — defined by SQLModel classes in `database/models/`, created by
  `create_db_and_tables()` (`SQLModel.metadata.create_all(engine)`), called once at
  FastAPI startup (`src/api/app.py`'s `lifespan`). This only creates tables that don't
  exist yet — it never alters an existing table's columns. For that, add a step to
  `database/migrations.py` using the helpers in `database/migration_helpers.py`
  (`add_column`, `drop_column`, `create_index`, `execute_sql`), which also runs once at
  startup, right after `create_db_and_tables()`.

Startup order (see `lifespan` in `src/api/app.py`): `create_db_and_tables()` →
`run_migrations(engine)` → app starts accepting requests. So a brand-new table defined
in a model appears with `create_all`, while a new column on an existing table needs an
explicit `add_column(...)` call in `migrations.py` — the two mechanisms don't overlap.

## Concurrency (multiple users, at the same time)

No code here does anything special "for" concurrency — it falls out of three
independent layers, each already described above:

1. **No shared server-side state between requests.** Auth is a stateless JWT decode
   (`get_current_user`) — there's no session object, no in-memory per-user cache,
   nothing two concurrent requests could race on at the app layer. User A's request and
   User B's request never touch any shared Python object except the connection pool.
2. **Sync route handlers run in a thread pool, not the event loop.** Every route in
   `src/api/routes/*.py` is `def`, not `async def` — FastAPI (via Starlette/anyio) runs
   sync handlers in a worker thread pool automatically, so a slow DB call in one
   request doesn't block other requests in the same process; they run concurrently on
   separate threads. `Dockerfile` also runs gunicorn with `-w 2`, so there are 2 full OS
   processes, each with its own thread pool, on top of that.
3. **Sessions are per-request, pooled connections are shared but finite.** Every store
   method opens and closes its own session (`with self.get_session() as session:`) —
   sessions are never held across requests, so there's no risk of one request's
   uncommitted work leaking into another's. The engine's pool
   (`pool_size=5, max_overflow=5` per process — see `config/settings.py`) caps how many
   concurrent DB operations can be in flight *per gunicorn worker* (so ~20 total across
   `-w 2`); once exhausted, a request waits briefly for a free connection rather than
   erroring, up to `pool_timeout`. If you raise gunicorn's worker count, raise or check
   this against Supabase's own connection limit too — the pooler on port 6543 (what
   `DATABASE_URL` should point at) is built to absorb many client connections cheaply,
   which is why we normalize to it in `config/settings.py`.

**Data isolation, not locking, is what keeps users out of each other's data.** Every
store method takes `user_id` and filters/checks by it (see `item_store.py`) — two users
hitting the API at the same instant simply can't see or touch each other's rows;
Postgres's own MVCC handles concurrent transactions on the same table safely without
any locking code here.

**Known gaps — acceptable for a boilerplate, worth knowing before a demo:**
- `ItemStore.update` is last-write-wins: two concurrent edits to the same row aren't
  optimistically checked, the second write silently overwrites the first. Add a
  version/`updated_at` check in the `WHERE` clause if you need real optimistic locking
  for a specific entity.
- No rate limiting or per-user request throttling anywhere.

## APIs & routes — how they're organized

- Every route module (`src/api/routes/*.py`) is a self-contained `APIRouter()` — no
  shared router, no global route list. `src/api/app.py` is the only file that knows
  about all of them (it imports each module and calls `app.include_router(...)`).
- URL structure: `app.include_router(items_routes.router, prefix="/api/items", ...)`
  means the router's own `@router.get("")` becomes `GET /api/items`, and
  `@router.get("/{item_id}")` becomes `GET /api/items/{item_id}` — the prefix is set
  once at registration, not repeated inside the route file.
- A route module never imports another route module or talks to the database directly
  — it only calls its corresponding store (`items_routes.py` → `item_store.py`,
  `auth_routes.py` → `user_store.py`). If a new route needs data from two entities,
  call both stores from the route, don't have one store call another.
- Every JSON response follows `{"status": "success", "data": ...}` (plus `"count"` for
  lists) so the frontend's response handling (`res.data.data` in `lib/api.ts` callers)
  is uniform across every endpoint — don't return bare objects/lists from a route.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill DATABASE_URL (Supabase), JWT_SECRET_KEY, GOOGLE_CLIENT_ID
uvicorn src.api.app:app --reload --port 8000
```

No Docker required for local dev — the Dockerfile is only for deploying to Render.
