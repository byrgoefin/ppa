"""Spansh Power Play bulk ingestion service.

Downloads powerplay.json.gz from Spansh and inserts a time-stamped snapshot
row for every system in the file.  Systems themselves are upserted so their
coordinates and allegiance stay current.

Schema of each object in the Spansh powerplay.json.gz array:
{
  "id64": 5031654888434,
  "name": "Cubeo",
  "x": 46.375, "y": -87.625, "z": -0.625,
  "power": "Arissa Lavigny-Duval",
  "powerState": "Fortified",
  "powerStateControlProgress": 0.0,
  "powerStateReinforcement": 12345,
  "powerStateUndermining": 678,
  "allegiance": "Empire",
  "population": 22000000
}
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

SPANSH_PP_URL = "https://downloads.spansh.co.uk/powerplay.json.gz"
BATCH_COMMIT_SIZE = 500


def run_spansh_ingest(db: Session) -> IngestionRun:
    """Stream-download the Spansh powerplay dump and store PP snapshots.

    Creates an IngestionRun audit row, upserts pp_systems, inserts
    pp_system_snapshots rows, and updates the run status on completion.
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
        logger.info("Downloading Spansh PP dump from %s", SPANSH_PP_URL)
        response = requests.get(SPANSH_PP_URL, stream=True, timeout=120)
        response.raise_for_status()
        response.raw.decode_content = True
        gzip_file = gzip.GzipFile(fileobj=response.raw, mode="rb")

        for system_obj in ijson.items(gzip_file, "item"):
            system_id64: int | None = system_obj.get("id64")
            if system_id64 is None:
                continue

            name: str = system_obj.get("name", "")
            x: float | None = system_obj.get("x")
            y: float | None = system_obj.get("y")
            z: float | None = system_obj.get("z")
            allegiance: str | None = system_obj.get("allegiance")
            population: int | None = system_obj.get("population")
            power: str | None = system_obj.get("power")
            power_state: str | None = system_obj.get("powerState")
            control_progress: float | None = system_obj.get("powerStateControlProgress")
            reinforcement: int | None = system_obj.get("powerStateReinforcement")
            undermining: int | None = system_obj.get("powerStateUndermining")

            # Upsert the system record (coordinates + allegiance may change)
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

            # Insert a fresh snapshot row (never upsert — we want full history)
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
            if records_processed % BATCH_COMMIT_SIZE == 0:
                db.commit()
                logger.debug("Spansh PP ingest: %d systems processed", records_processed)

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
            "Spansh PP ingest completed: %d systems (run_id=%d)",
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
