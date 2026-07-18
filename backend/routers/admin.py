"""Admin router — ingest triggers, status, and settings (JWT-gated)."""

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.models import AdminSetting, IngestionRun
from models.schemas import AdminSettingSchema, IngestionRunSchema
from routers.deps import AdminUserDep, get_db
from services.ingestion import run_spansh_ingest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def run_spansh_ingest_task() -> None:
    """Wrapper used by both BackgroundTasks and APScheduler."""
    db = SessionLocal()
    try:
        run_spansh_ingest(db)
    except Exception:
        logger.exception("Background Spansh PP ingest task failed")
    finally:
        db.close()


@router.get("/health")
async def admin_health(admin: AdminUserDep) -> dict:
    return {"status": "ok", "router": "admin", "admin_email": admin["email"]}


@router.get("/status")
def get_status(request: Request, admin: AdminUserDep, db: Session = Depends(get_db)) -> dict:
    """Return the 10 most recent ingestion runs and scheduler next-run time."""
    spansh_next: str | None = None
    try:
        scheduler = getattr(request.app.state, "scheduler", None)
        if scheduler:
            job = scheduler.get_job("spansh_ingest")
            if job and job.next_run_time:
                spansh_next = job.next_run_time.isoformat()
    except Exception:
        pass

    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .limit(10)
        .all()
    )
    return {
        "recent_runs": [IngestionRunSchema.model_validate(r) for r in runs],
        "spansh_next_run": spansh_next,
    }


@router.get("/settings")
def get_settings(admin: AdminUserDep, db: Session = Depends(get_db)) -> list[AdminSettingSchema]:
    return db.query(AdminSetting).all()


class SettingUpdate(BaseModel):
    key: str
    value: str


@router.patch("/settings")
def update_settings(
    updates: list[SettingUpdate],
    admin: AdminUserDep,
    db: Session = Depends(get_db),
) -> list[AdminSettingSchema]:
    for update in updates:
        existing = db.query(AdminSetting).filter(AdminSetting.key == update.key).first()
        if existing:
            existing.value = update.value
        else:
            db.add(AdminSetting(key=update.key, value=update.value))
    db.commit()
    return db.query(AdminSetting).all()


@router.post("/ingest/spansh")
async def trigger_spansh_ingest(
    background_tasks: BackgroundTasks,
    admin: AdminUserDep,
) -> dict:
    """Kick off a Spansh Power Play ingest in the background."""
    background_tasks.add_task(run_spansh_ingest_task)
    logger.info("Spansh PP ingest triggered manually by %s", admin["email"])
    return {"message": "Spansh PP ingest started in background"}
