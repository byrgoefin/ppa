"""Pydantic v2 response schemas for the Elite Powerplay API."""

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
# Power Play system entry (latest snapshot joined)
# ---------------------------------------------------------------------------


class PPSystemEntry(BaseModel):
    """A system under a Power's influence, enriched with its latest PP snapshot."""

    system_id64: int
    name: str
    x: float
    y: float
    z: float
    allegiance: Optional[str] = None
    population: Optional[int] = None

    # Latest snapshot fields
    power: Optional[str] = None
    power_state: Optional[str] = None
    reinforcement: Optional[int] = None
    undermining: Optional[int] = None
    control_progress: Optional[float] = None
    snapshot_time: Optional[datetime] = None

    # Computed
    distance_from_center: Optional[float] = None
    # Derived ratio 0.0–1.0 (undermining / reinforcement); None if no data
    undermine_ratio: Optional[float] = None


# ---------------------------------------------------------------------------
# System history point
# ---------------------------------------------------------------------------


class SystemHistoryPoint(BaseModel):
    model_config = _from_orm

    snapshot_time: datetime
    power: Optional[str] = None
    power_state: Optional[str] = None
    reinforcement: Optional[int] = None
    undermining: Optional[int] = None
    control_progress: Optional[float] = None


# ---------------------------------------------------------------------------
# System search result
# ---------------------------------------------------------------------------


class SystemSearchResult(BaseModel):
    model_config = _from_orm

    system_id64: int
    name: str
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None


# ---------------------------------------------------------------------------
# Powers list
# ---------------------------------------------------------------------------


class PowersList(BaseModel):
    powers: list[str]


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------


class RecommendationItem(BaseModel):
    system_id64: int
    system_name: str
    score: float
    type: str                       # "fortify" | "expand"
    reasons: list[str]
    power_state: Optional[str] = None
    reinforcement: Optional[int] = None
    undermining: Optional[int] = None
    undermine_ratio: Optional[float] = None
    distance_from_center: Optional[float] = None
    # "rising" | "falling" | "stable" | "unknown"  (based on undermine_ratio trend)
    threat_trend: str = "unknown"


class RecommendationsResponse(BaseModel):
    fortify: list[RecommendationItem]
    expand: list[RecommendationItem]
    llm_summary: Optional[str] = None
