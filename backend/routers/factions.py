"""Factions router — stub implementation (full queries in Sub-Task 4)."""

from fastapi import APIRouter

router = APIRouter(prefix="/factions", tags=["factions"])


@router.get("/health")
async def factions_health() -> dict:
    """Liveness probe for the factions router."""
    return {"status": "ok", "router": "factions"}
