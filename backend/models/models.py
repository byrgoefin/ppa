"""SQLAlchemy ORM models for the Elite Dangerous Power Play Analyzer."""

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
# ingestion_runs — must be defined first (other tables FK into it)
# ---------------------------------------------------------------------------


class IngestionRun(Base):
    """Audit log entry for each Spansh or EDSM ingestion job."""

    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, index=True)
    # "spansh" or "edsm"
    source = Column(String(32), nullable=False)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    # "running" | "completed" | "failed"
    status = Column(String(16), nullable=False, default="running")
    records_processed = Column(Integer, nullable=False, default=0)

    faction_presences = relationship("FactionPresence", back_populates="ingestion_run")
    pp_snapshots = relationship("PPSnapshot", back_populates="ingestion_run")


# ---------------------------------------------------------------------------
# factions
# ---------------------------------------------------------------------------


class Faction(Base):
    """A minor faction as extracted from the Spansh bulk download."""

    __tablename__ = "factions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    allegiance = Column(String(128), nullable=True)
    government = Column(String(128), nullable=True)

    presences = relationship("FactionPresence", back_populates="faction")


# ---------------------------------------------------------------------------
# systems
# ---------------------------------------------------------------------------


class System(Base):
    """A star system, keyed by its 64-bit system ID from Spansh."""

    __tablename__ = "systems"

    id = Column(Integer, primary_key=True, index=True)
    # Elite Dangerous 64-bit system ID — up to ~93 quadrillion
    system_id64 = Column(BigInteger, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    z = Column(Float, nullable=True)

    presences = relationship("FactionPresence", back_populates="system")
    pp_snapshots = relationship("PPSnapshot", back_populates="system")


# ---------------------------------------------------------------------------
# faction_presence
# ---------------------------------------------------------------------------


class FactionPresence(Base):
    """
    Records that a faction has presence in a system for a given ingestion run.

    Rows are inserted per run; old runs' rows remain for historical reference.
    Never updated — each run inserts fresh rows linked to its ingestion_run_id.
    """

    __tablename__ = "faction_presence"

    id = Column(Integer, primary_key=True, index=True)
    faction_id = Column(Integer, ForeignKey("factions.id"), nullable=False, index=True)
    system_id = Column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    is_controlling = Column(Boolean, nullable=False, default=False)
    ingestion_run_id = Column(
        Integer, ForeignKey("ingestion_runs.id"), nullable=False, index=True
    )

    faction = relationship("Faction", back_populates="presences")
    system = relationship("System", back_populates="presences")
    ingestion_run = relationship("IngestionRun", back_populates="faction_presences")


# ---------------------------------------------------------------------------
# pp_snapshots  (insert-only — never update)
# ---------------------------------------------------------------------------


class PPSnapshot(Base):
    """
    A time-stamped snapshot of a system's Power Play state and controlling
    faction influence, sourced from the EDSM API.

    Rows are NEVER updated — each EDSM sync appends new rows so historical
    trends accumulate over time.
    """

    __tablename__ = "pp_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer, ForeignKey("systems.id"), nullable=False, index=True)
    # Power Play power name (e.g. "Aisling Duval") — nullable if system is unpopulated
    pp_power = Column(String(255), nullable=True)
    # Power Play state string as returned by EDSM (e.g. "Fortified", "Undermined")
    pp_state = Column(String(64), nullable=True)
    # Controlling faction influence 0.0–1.0; None if EDSM doesn't return it
    influence = Column(Float, nullable=True)
    snapshot_time = Column(DateTime, default=func.now(), nullable=False, index=True)
    ingestion_run_id = Column(
        Integer, ForeignKey("ingestion_runs.id"), nullable=True, index=True
    )

    system = relationship("System", back_populates="pp_snapshots")
    ingestion_run = relationship("IngestionRun", back_populates="pp_snapshots")


# ---------------------------------------------------------------------------
# admin_settings
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
