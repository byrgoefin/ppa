"""Systems router — stub implementation (full queries in Sub-Task 4)."""

from fastapi import APIRouter

router = APIRouter(prefix="/systems", tags=["systems"])


@router.get("/health")
async def systems_health() -> dict:
    """Liveness probe for the systems router."""
    return {"status": "ok", "router": "systems"}
