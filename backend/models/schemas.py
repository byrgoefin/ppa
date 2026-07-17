"""Pydantic v2 response schemas for the Elite Powerplay API.

All schemas use ``model_config = ConfigDict(from_attributes=True)``
so they can be constructed directly from SQLAlchemy ORM instances.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

_from_orm = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# IngestionRun
# ---------------------------------------------------------------------------


class IngestionRunSchema(BaseModel):
    model_config = _from_orm

    id: int
    source: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_processed: int


# ---------------------------------------------------------------------------
# AdminSetting
# ---------------------------------------------------------------------------


class AdminSettingSchema(BaseModel):
    model_config = _from_orm

    id: int
    key: str
    value: str


# ---------------------------------------------------------------------------
# Faction list / search
# ---------------------------------------------------------------------------


class FactionListItem(BaseModel):
    model_config = _from_orm

    id: int
    name: str
    allegiance: Optional[str] = None
    government: Optional[str] = None
    system_count: int = 0


# ---------------------------------------------------------------------------
# Per-system entry for a faction's territory view
# ---------------------------------------------------------------------------


class Coords(BaseModel):
    x: float
    y: float
    z: float


class FactionSystemEntry(BaseModel):
    """A system in which a faction has presence, enriched with latest PP state."""

    model_config = _from_orm

    system_name: str
    system_id64: int
    is_controlling: bool
    coords: Optional[Coords] = None
    pp_state: Optional[str] = None
    pp_power: Optional[str] = None
    # 0.0–1.0; multiply by 100 for display as a percentage
    influence: Optional[float] = None
    # Computed when caller supplies a center system; Euclidean LY distance
    distance_from_center: Optional[float] = None


# ---------------------------------------------------------------------------
# System PP history
# ---------------------------------------------------------------------------


class SystemHistoryPoint(BaseModel):
    model_config = _from_orm

    snapshot_time: datetime
    pp_state: Optional[str] = None
    pp_power: Optional[str] = None
    influence: Optional[float] = None


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------


class RecommendationItem(BaseModel):
    system_name: str
    system_id64: int
    # Computed score (higher = more important action)
    score: float
    # "fortify" or "expand"
    type: str
    # Human-readable explanations for the score
    reasons: list[str]
    distance_from_center: Optional[float] = None
    pp_state: Optional[str] = None
    influence: Optional[float] = None
    # "rising" | "falling" | "stable" | "unknown"
    influence_trend: str = "unknown"
