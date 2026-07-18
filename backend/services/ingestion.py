"""Spansh Power Play bulk ingestion service.

Data source: https://downloads.spansh.co.uk/systems_populated.json.gz

Each object in the array has these PP-relevant fields (PP 2.0 schema):
{
  "id64": 10477373803,
  "name": "Sol",
  "coords": {"x": 0.0, "y": 0.0, "z": 0.0},
  "allegiance": "Federation",
  "population": 18320926115,
  "controlling_power": "Jerome Archer",        -- single controlling power (may be null)
  "power": ["Aisling Duval", "Jerome Archer"], -- all powers with presence
  "power_state": "Stronghold",                 -- Stronghold|Fortified|Exploited|Turmoil|
                                               --   InPrepareRadius|Prepared|Expansion|Contested
  "power_state_control_progress": 0.649698,
  "power_state_reinforcement": 66756,
  "power_state_undermining": 124458,
  "updated_at": "2026-07-18 03:51:09+00"
}

Systems with no PP presence have null/missing power fields — we skip those.
We store one row per controlling_power per system so each power's territory
can be queried independently.
"""

import gzip
import logging
from datetime import datetime

import ijson
import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.models import IngestionRun

logger = logging.getLogger(__name__)

SPANSH_PP_URL = "https://downloads.spansh.co.uk/systems_populated.json.gz"
BATCH_COMMIT_SIZE = 500


def run_spansh_ingest(db: Session) -> IngestionRun:
    """Stream-download the Spansh systems_populated dump and store PP snapshots.

    Only systems that have a ``controlling_power`` value are stored.
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
    logger.info("Spansh PP ingest started (run_id=%d)", run_id)

    records_processed = 0

    try:
        logger.info("Downloading Spansh systems_populated dump from %s", SPANSH_PP_URL)
        response = requests.get(SPANSH_PP_URL, stream=True, timeout=120)
        response.raise_for_status()
        response.raw.decode_content = True
        gzip_file = gzip.GzipFile(fileobj=response.raw, mode="rb")

        for system_obj in ijson.items(gzip_file, "item"):
            # Skip systems with no PP controlling power
            controlling_power: str | None = system_obj.get("controlling_power")
            if not controlling_power:
                continue

            system_id64: int | None = system_obj.get("id64")
            if system_id64 is None:
                continue

            name: str = system_obj.get("name", "")
            coords = system_obj.get("coords") or {}
            x: float | None = coords.get("x")
            y: float | None = coords.get("y")
            z: float | None = coords.get("z")
            allegiance: str | None = system_obj.get("allegiance")
            population: int | None = system_obj.get("population")
            power_state: str | None = system_obj.get("power_state")
            control_progress: float | None = system_obj.get("power_state_control_progress")
            reinforcement: int | None = system_obj.get("power_state_reinforcement")
            undermining: int | None = system_obj.get("power_state_undermining")

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

            # Insert a fresh snapshot row (insert-only for full history)
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
                    "power": controlling_power,
                    "power_state": power_state,
                    "control_progress": control_progress,
                    "reinforcement": reinforcement,
                    "undermining": undermining,
                },
            )

            records_processed += 1
            if records_processed % BATCH_COMMIT_SIZE == 0:
                db.commit()
                logger.debug("Spansh PP ingest: %d PP systems processed", records_processed)

        db.commit()
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
            "Spansh PP ingest completed: %d PP systems (run_id=%d)",
            records_processed, run_id,
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
