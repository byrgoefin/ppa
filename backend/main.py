"""Elite Dangerous Power Play Analyzer — FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Import engine + Base, and all models so their tables are registered on Base.metadata.
from db.session import Base, engine  # noqa: E402
import models.models  # noqa: F401

# Create all tables that don't yet exist (idempotent on every startup).
Base.metadata.create_all(bind=engine)

from routers import auth, factions, systems, admin  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — APScheduler startup/shutdown (stub; jobs wired in Sub-Tasks 2/3)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Scheduler startup placeholder — Sub-Tasks 2 & 3 wire actual jobs here.
    logger.info("Elite Powerplay API starting up.")
    yield
    logger.info("Elite Powerplay API shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Elite Dangerous Power Play Analyzer API",
    description="Backend for the Elite Dangerous Power Play Analyzer",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow all origins during development; tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(factions.router, prefix=API_PREFIX)
app.include_router(systems.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """Basic liveness probe."""
    return {"status": "ok"}
