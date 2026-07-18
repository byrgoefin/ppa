"""Powers router — read-only public endpoints for Power Play data."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import get_db
from models.models import PPSystem, PPSystemSnapshot
from models.schemas import (
    PPSystemEntry,
    PowersList,
    RecommendationsResponse,
    SystemHistoryPoint,
    SystemSearchResult,
)
from services.scoring import compute_recommendations

router = APIRouter(prefix="/powers", tags=["powers"])


# ---------------------------------------------------------------------------
# GET /api/powers  — list all known powers from latest snapshots
# ---------------------------------------------------------------------------


@router.get("", response_model=PowersList)
def list_powers(db: Session = Depends(get_db)) -> PowersList:
    """Return all distinct power names present in the latest snapshot data."""
    rows = db.execute(
        text("""
            SELECT DISTINCT power
            FROM pp_system_snapshots
            WHERE power IS NOT NULL
            ORDER BY power
        """)
    ).all()
    return PowersList(powers=[r.power for r in rows])


# ---------------------------------------------------------------------------
# GET /api/powers/search  — autocomplete for power names
# ---------------------------------------------------------------------------


@router.get("/search", response_model=PowersList)
def search_powers(
    q: str = Query(default="", min_length=1),
    db: Session = Depends(get_db),
) -> PowersList:
    """Case-insensitive substring search over power names."""
    rows = db.execute(
        text("""
            SELECT DISTINCT power
            FROM pp_system_snapshots
            WHERE power ILIKE :q
            ORDER BY power
            LIMIT 20
        """),
        {"q": f"%{q}%"},
    ).all()
    return PowersList(powers=[r.power for r in rows])


# ---------------------------------------------------------------------------
# GET /api/powers/{name}/systems  — all systems for a power
# ---------------------------------------------------------------------------


@router.get("/{name}/systems", response_model=list[PPSystemEntry])
def get_power_systems(
    name: str,
    center_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PPSystemEntry]:
    """
    Return all systems currently under the given Power's influence,
    enriched with their latest PP snapshot.  Optionally compute distance
    from a center system when center_id (system_id64) is supplied.
    """
    # Latest snapshot per system
    latest_sql = text("""
        SELECT DISTINCT ON (system_id)
               system_id, power, power_state,
               reinforcement, undermining, control_progress, snapshot_time
        FROM pp_system_snapshots
        WHERE power = :power
        ORDER BY system_id, snapshot_time DESC
    """)
    snap_rows = db.execute(latest_sql, {"power": name}).mappings().all()

    if not snap_rows:
        return []

    system_ids = [r["system_id"] for r in snap_rows]
    snap_by_id = {r["system_id"]: r for r in snap_rows}

    systems = db.query(PPSystem).filter(PPSystem.id.in_(system_ids)).all()
    sys_by_id = {s.id: s for s in systems}

    # Resolve center coords
    cx: Optional[float] = None
    cy: Optional[float] = None
    cz: Optional[float] = None
    if center_id is not None:
        center_sys = db.query(PPSystem).filter(PPSystem.system_id64 == center_id).first()
        if center_sys:
            cx, cy, cz = center_sys.x, center_sys.y, center_sys.z

    results: list[PPSystemEntry] = []
    for sid, snap in snap_by_id.items():
        system = sys_by_id.get(sid)
        if system is None:
            continue

        x = system.x or 0.0
        y = system.y or 0.0
        z = system.z or 0.0

        distance: Optional[float] = None
        if cx is not None and cy is not None and cz is not None:
            distance = math.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2)

        rein = snap["reinforcement"]
        under = snap["undermining"]
        undermine_ratio: Optional[float] = None
        if rein and rein > 0 and under is not None:
            undermine_ratio = under / rein

        results.append(PPSystemEntry(
            system_id64=system.system_id64,
            name=system.name,
            x=x, y=y, z=z,
            allegiance=system.allegiance,
            population=system.population,
            power=snap["power"],
            power_state=snap["power_state"],
            reinforcement=rein,
            undermining=under,
            control_progress=snap["control_progress"],
            snapshot_time=snap["snapshot_time"],
            distance_from_center=distance,
            undermine_ratio=undermine_ratio,
        ))

    return results


# ---------------------------------------------------------------------------
# GET /api/powers/{name}/recommendations
# ---------------------------------------------------------------------------


@router.get("/{name}/recommendations", response_model=RecommendationsResponse)
def get_power_recommendations(
    name: str,
    center_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> RecommendationsResponse:
    """Return fortify and expand recommendations for a Power."""
    result = compute_recommendations(name, center_id, db)
    return RecommendationsResponse(**result)


# ---------------------------------------------------------------------------
# GET /api/systems/search  — system name search (for center system selector)
# ---------------------------------------------------------------------------

systems_router = APIRouter(prefix="/systems", tags=["systems"])


@systems_router.get("/search", response_model=list[SystemSearchResult])
def search_systems(
    q: str = Query(default="", min_length=1),
    db: Session = Depends(get_db),
) -> list[SystemSearchResult]:
    """Case-insensitive substring search over known PP system names (max 20)."""
    rows = (
        db.query(PPSystem)
        .filter(PPSystem.name.ilike(f"%{q}%"))
        .order_by(PPSystem.name)
        .limit(20)
        .all()
    )
    return [
        SystemSearchResult(system_id64=s.system_id64, name=s.name, x=s.x, y=s.y, z=s.z)
        for s in rows
    ]


@systems_router.get("/{system_id64}/history", response_model=list[SystemHistoryPoint])
def get_system_history(
    system_id64: int,
    db: Session = Depends(get_db),
) -> list[SystemHistoryPoint]:
    """Return all PP snapshots for a system, ordered chronologically."""
    system = db.query(PPSystem).filter(PPSystem.system_id64 == system_id64).first()
    if system is None:
        return []
    rows = (
        db.query(PPSystemSnapshot)
        .filter(PPSystemSnapshot.system_id == system.id)
        .order_by(PPSystemSnapshot.snapshot_time.asc())
        .all()
    )
    return [
        SystemHistoryPoint(
            snapshot_time=r.snapshot_time,
            power=r.power,
            power_state=r.power_state,
            reinforcement=r.reinforcement,
            undermining=r.undermining,
            control_progress=r.control_progress,
        )
        for r in rows
    ]
