# FastAPI application entrypoint. Wires settings, DB startup, CORS, and route modules.

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from database.migrations import run_migrations
from database.session import create_db_and_tables, engine
from src.api.routes import auth_routes, cart_routes, health, products_routes
from src.services.seed_data import seed_promos

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) create missing tables  2) alter/drop migrations  3) seed demo promos
    await create_db_and_tables()
    await run_migrations(engine)
    await seed_promos()
    logger.info("startup complete: tables ready, promos seeded")
    yield


app = FastAPI(title="Promo Engine API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(products_routes.router, prefix="/api/products", tags=["products"])
app.include_router(cart_routes.router, prefix="/api/cart", tags=["cart"])
