# FastAPI application entrypoint. Why it's here: this is the one file that wires
# everything else together — settings, DB startup, CORS, and every route module — into
# the `app` object that uvicorn/gunicorn actually serves (see Dockerfile's CMD).

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from database.migrations import run_migrations
from database.session import create_db_and_tables, engine
from src.api.routes import auth_routes, health, items_routes

# Python's root logger has no handler by default, so module-level `logger.info(...)`
# calls (e.g. src/services/background_tasks.py) are silently dropped otherwise — this
# is what makes background-task logs actually show up in `uvicorn`'s console/Render's
# log stream.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server process starts (not per-request): create any tables
    # that don't exist yet, then apply any pending column-level migrations. Awaited
    # because both now run against the async engine (see database/session.py).
    await create_db_and_tables()
    await run_migrations(engine)
    yield


app = FastAPI(title="Boilerplate API", version="0.1.0", lifespan=lifespan)

# Lets the Next.js frontend (a different origin) call this API from the browser.
# allow_credentials=True is harmless here since we don't use cookies, but is needed if
# you ever switch the JWT from a header to an httpOnly cookie.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register each route module's router. New entity? Add its routes module to the import
# above and one `include_router` line here — see AGENTS.md for the full pattern.
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(items_routes.router, prefix="/api/items", tags=["items"])
