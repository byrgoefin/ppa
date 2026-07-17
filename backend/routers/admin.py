"""Admin router — stub implementation (full endpoints in Sub-Tasks 2, 3, 10)."""

from fastapi import APIRouter

from routers.deps import AdminUserDep

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def admin_health(admin: AdminUserDep) -> dict:
    """Liveness probe for the admin router (requires valid admin JWT)."""
    return {"status": "ok", "router": "admin", "admin_email": admin["email"]}
