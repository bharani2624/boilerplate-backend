from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from database.migrations import run_migrations
from database.session import create_db_and_tables, engine
from src.api.routes import auth_routes, health, items_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    run_migrations(engine)
    yield


app = FastAPI(title="Boilerplate API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(items_routes.router, prefix="/api/items", tags=["items"])
