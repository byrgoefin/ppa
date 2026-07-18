"""Spansh Power Play ingestion service — uses the Spansh search API.

Data source: POST https://spansh.co.uk/api/systems/search
             with filter controlling_power = <power name>

This is the correct source for PP 2.0 data.  The bulk download files
(systems_populated.json.gz, galaxy.json.gz) do NOT contain PP fields.

Actual PP 2.0 schema from the Spansh API (confirmed 2026-07):
{
  "id64": 203174175932,
  "name": "52 h2 Sagittarii",
  "x": -46.0,
  "y": -68.3125,
  "z": 170.8125,
  "allegiance": "Independent",
  "population": 68496,
  "controlling_power": "Aisling Duval",
  "power": ["Aisling Duval"],
  "power_state": "Exploited",         -- Exploited | Fortified | Stronghold | Unoccupied
  "power_state_control_progress": 0.259166,
  "power_state_reinforcement": 0,
  "power_state_undermining": 291,
  "updated_at": "2026-07-17 18:46:04+00"
}

Coords are FLAT (x/y/z at top level, not nested).
Power name for Arissa is "A. Lavigny-Duval" (abbreviated), not full name.

Known powers (from field_values endpoint, July 2026):
  A. Lavigny-Duval, Aisling Duval, Archon Delaine, Denton Patreus,
  Edmund Mahon, Felicia Winters, Jerome Archer, Li Yong-Rui,
  Nakato Kaine, Pranav Antal, Yuri Grom, Zemina Torval

Known PP states (from field_values endpoint):
  Exploited (13,263 systems), Fortified (2,827), Stronghold (1,414),
  Unoccupied (34,949 — systems with PP presence but no controlling power)

We ingest ALL powers in a single run so the full galaxy picture is available.
For each power we page through the search API 500 systems at a time.
"""

import logging
import time
from datetime import datetime
from typing import Optional

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.models import IngestionRun

logger = logging.getLogger(__name__)

SPANSH_SEARCH_URL = "https://spansh.co.uk/api/systems/search"
PAGE_SIZE = 500          # max Spansh allows per request
REQUEST_DELAY = 0.25     # seconds between pages — be polite to Spansh
BATCH_COMMIT_SIZE = 500  # DB commit frequency

# All known powers as of July 2026 (abbreviated names as Spansh returns them)
ALL_POWERS = [
    "A. Lavigny-Duval",
    "Aisling Duval",
    "Archon Delaine",
    "Denton Patreus",
    "Edmund Mahon",
    "Felicia Winters",
    "Jerome Archer",
    "Li Yong-Rui",
    "Nakato Kaine",
    "Pranav Antal",
    "Yuri Grom",
    "Zemina Torval",
]

# ---------------------------------------------------------------------------
# Spansh API helpers
# ---------------------------------------------------------------------------


def _fetch_page(power: str, page: int) -> dict:
    """Fetch one page of systems for a power from the Spansh search API."""
    payload = {
        "filters": {
            "controlling_power": {"value": [power], "comparison": "="}
        },
        "size": PAGE_SIZE,
        "page": page,
        "sort": [{"id64": {"direction": "asc"}}],
    }
    resp = requests.post(SPANSH_SEARCH_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _iter_power_systems(power: str):
    """Yield all system dicts for a given power, paging through the API."""
    page = 0
    total_reported = None

    while True:
        logger.debug("Fetching page %d for power '%s'", page, power)
        data = _fetch_page(power, page)

        if total_reported is None:
            total_reported = data.get("count", 0)
            logger.info("  Power '%s': %d systems reported by API", power, total_reported)

        results = data.get("results", [])
        if not results:
            break

        yield from results
        page += 1

        # Stop if we've seen all systems (avoid infinite loop on API quirks)
        if total_reported is not None and (page * PAGE_SIZE) >= total_reported:
            break

        time.sleep(REQUEST_DELAY)


# ---------------------------------------------------------------------------
# Main ingest entry point
# ---------------------------------------------------------------------------


def run_spansh_ingest(db: Session) -> IngestionRun:
    """Fetch PP system data from the Spansh search API and store snapshots.

    Iterates over all known Powers, paging through the Spansh search API
    500 systems at a time.  Inserts one pp_system_snapshots row per system
    per call (insert-only) so the full history accumulates.
    """
    run = IngestionRun(
        source="spansh_pp",
        status="running",
        started_at=datetime.utcnow(),
        records_processed=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id: int = run.id
    logger.info("Spansh PP ingest started via search API (run_id=%d)", run_id)

    records_processed = 0

    try:
        for power in ALL_POWERS:
            logger.info("Ingesting power: %s", power)
            power_count = 0

            for system_obj in _iter_power_systems(power):
                system_id64: Optional[int] = system_obj.get("id64")
                if system_id64 is None:
                    continue

                name: str = system_obj.get("name", "")

                # Coords are flat in the API response
                x: Optional[float] = system_obj.get("x")
                y: Optional[float] = system_obj.get("y")
                z: Optional[float] = system_obj.get("z")
                # Fallback: try nested coords dict (future-proofing)
                if x is None:
                    coords = system_obj.get("coords") or {}
                    x = coords.get("x")
                    y = coords.get("y")
                    z = coords.get("z")

                allegiance: Optional[str]  = system_obj.get("allegiance")
                population: Optional[int]  = system_obj.get("population")
                power_state: Optional[str] = system_obj.get("power_state")
                control_progress: Optional[float] = system_obj.get("power_state_control_progress")
                reinforcement: Optional[int] = system_obj.get("power_state_reinforcement")
                undermining: Optional[int]   = system_obj.get("power_state_undermining")

                # Upsert the system record
                sys_result = db.execute(
                    text("""
                        INSERT INTO pp_systems (system_id64, name, x, y, z, allegiance, population)
                        VALUES (:id64, :name, :x, :y, :z, :allegiance, :population)
                        ON CONFLICT (system_id64) DO UPDATE
                            SET name       = EXCLUDED.name,
                                x          = EXCLUDED.x,
                                y          = EXCLUDED.y,
                                z          = EXCLUDED.z,
                                allegiance = EXCLUDED.allegiance,
                                population = EXCLUDED.population
                        RETURNING id
                    """),
                    {
                        "id64": system_id64, "name": name,
                        "x": x, "y": y, "z": z,
                        "allegiance": allegiance, "population": population,
                    },
                )
                system_db_id: int = sys_result.scalar_one()

                # Insert a fresh snapshot row (insert-only for history)
                db.execute(
                    text("""
                        INSERT INTO pp_system_snapshots
                            (system_id, ingestion_run_id, snapshot_time,
                             power, power_state, control_progress,
                             reinforcement, undermining)
                        VALUES
                            (:system_id, :run_id, :now,
                             :power, :power_state, :control_progress,
                             :reinforcement, :undermining)
                    """),
                    {
                        "system_id": system_db_id,
                        "run_id": run_id,
                        "now": datetime.utcnow(),
                        "power": power,
                        "power_state": power_state,
                        "control_progress": control_progress,
                        "reinforcement": reinforcement,
                        "undermining": undermining,
                    },
                )

                records_processed += 1
                power_count += 1
                if records_processed % BATCH_COMMIT_SIZE == 0:
                    db.commit()
                    logger.debug("  … %d total records committed", records_processed)

            db.commit()
            logger.info("  Finished '%s': %d systems stored", power, power_count)

        # Final update
        db.execute(
            text("""
                UPDATE ingestion_runs
                SET status = 'completed', completed_at = :now, records_processed = :count
                WHERE id = :run_id
            """),
            {"now": datetime.utcnow(), "count": records_processed, "run_id": run_id},
        )
        db.commit()
        db.refresh(run)
        logger.info(
            "Spansh PP ingest complete: %d total systems across %d powers (run_id=%d)",
            records_processed, len(ALL_POWERS), run_id,
        )

    except Exception:
        logger.exception("Spansh PP ingest failed (run_id=%d)", run_id)
        try:
            db.execute(
                text("UPDATE ingestion_runs SET status = 'failed' WHERE id = :id"),
                {"id": run_id},
            )
            db.commit()
        except Exception:
            db.rollback()
        raise

    return run
