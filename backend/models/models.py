"""SQLAlchemy ORM models for the Elite Dangerous Power Play Analyzer.

Data is sourced from the Spansh Power Play dump (powerplay.json.gz) which
contains one entry per system that is currently under a Power's influence.
Each sync run inserts a fresh snapshot row so historical trends accumulate.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from db.session import Base


# ---------------------------------------------------------------------------
# ingestion_runs — audit log for each sync job
# ---------------------------------------------------------------------------


class IngestionRun(Base):
    """Audit log entry for each Spansh Power Play ingestion job."""

    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(32), nullable=False)          # "spansh_pp"
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False, default="running")  # running|completed|failed
    records_processed = Column(Integer, nullable=False, default=0)

    snapshots = relationship("PPSystemSnapshot", back_populates="ingestion_run")


# ---------------------------------------------------------------------------
# pp_systems — one row per unique star system (upserted each ingest)
# ---------------------------------------------------------------------------


class PPSystem(Base):
    """A star system that is (or has been) under a Power's influence."""

    __tablename__ = "pp_systems"

    id = Column(Integer, primary_key=True, index=True)
    system_id64 = Column(BigInteger, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    z = Column(Float, nullable=True)
    allegiance = Column(String(128), nullable=True)
    population = Column(BigInteger, nullable=True)

    snapshots = relationship("PPSystemSnapshot", back_populates="system")


# ---------------------------------------------------------------------------
# pp_system_snapshots — insert-only time-series per system per ingest run
# ---------------------------------------------------------------------------


class PPSystemSnapshot(Base):
    """
    A point-in-time snapshot of a system's Power Play state.

    One row is inserted per system per ingestion run — never updated.
    This gives us the full history needed for trend analysis.
    """

    __tablename__ = "pp_system_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("pp_systems.id"), nullable=False, index=True)
    ingestion_run_id = Column(Integer, ForeignKey("ingestion_runs.id"), nullable=False, index=True)
    snapshot_time = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Power Play fields from Spansh dump
    power = Column(String(128), nullable=True, index=True)   # e.g. "Arissa Lavigny-Duval"
    power_state = Column(String(64), nullable=True)           # Fortified|Undermined|Turmoil|Expansion|Contested|HomeSystem|InPrepareRadius
    # Reinforcement and undermining progress (raw commodity counts from Spansh)
    reinforcement = Column(Integer, nullable=True)
    undermining = Column(Integer, nullable=True)
    # 0.0–1.0 control progress toward next state
    control_progress = Column(Float, nullable=True)

    system = relationship("PPSystem", back_populates="snapshots")
    ingestion_run = relationship("IngestionRun", back_populates="snapshots")


# ---------------------------------------------------------------------------
# admin_settings — scoring weight key/value store
# ---------------------------------------------------------------------------


class AdminSetting(Base):
    """Key/value store for scoring weights and app configuration."""

    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), unique=True, index=True, nullable=False)
    value = Column(String(512), nullable=False)


# ---------------------------------------------------------------------------
# admin_users
# ---------------------------------------------------------------------------


class AdminUser(Base):
    """Admin accounts for the JWT-gated admin panel."""

    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
