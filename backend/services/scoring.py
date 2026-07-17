"""Rule-based recommendation scoring engine.

Public entry point::

    compute_recommendations(faction_name, center_system_id64, db)
        -> {"fortify": [RecommendationItem, ...],
            "expand":  [RecommendationItem, ...],
            "llm_summary": None}

Scoring weights are loaded from the ``admin_settings`` table with
hard-coded defaults used for any key that is not present in the DB.
"""

from __future__ import annotations

import math
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.models import AdminSetting, Faction, FactionPresence, PPSnapshot, System
from models.schemas import RecommendationItem

# ---------------------------------------------------------------------------
# Default scoring weights
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, float] = {
    "fortify_undermined": 50.0,
    "fortify_turmoil": 40.0,
    "fortify_low_influence": 20.0,
    "fortify_trend_down": 15.0,
    "fortify_not_controlling": 25.0,
    "fortify_near_center": 10.0,
    "expand_uncontrolled": 40.0,
    "expand_proximity": 20.0,
    "expand_pp_state": 30.0,
    "expand_allegiance_gap": 10.0,
    "expand_low_competition": 15.0,
}


# ---------------------------------------------------------------------------
# Step 1: Load scoring weights
# ---------------------------------------------------------------------------


def load_weights(db: Session) -> dict[str, float]:
    """Return scoring weights, merging DB overrides on top of code defaults."""
    rows = db.query(AdminSetting).all()
    weights = dict(DEFAULTS)
    for row in rows:
        if row.key in weights:
            try:
                weights[row.key] = float(row.value)
            except (ValueError, TypeError):
                pass  # keep default if value is non-numeric
    return weights


# ---------------------------------------------------------------------------
# Step 2: Influence trend
# ---------------------------------------------------------------------------


def get_influence_trend(system_id: int, db: Session) -> str:
    """Return 'rising', 'falling', 'stable', or 'unknown' for a system.

    Compares the last 3 ``pp_snapshots`` rows (newest first).  Requires at
    least 2 non-null influence values to produce a directional result.
    """
    rows = (
        db.query(PPSnapshot.influence)
        .filter(PPSnapshot.system_id == system_id)
        .order_by(PPSnapshot.snapshot_time.desc())
        .limit(3)
        .all()
    )
    # Extract non-null values in newest-first order
    values = [r.influence for r in rows if r.influence is not None]
    if len(values) < 2:
        return "unknown"
    # values[0] is the most recent; values[-1] is the oldest of the set
    # "falling": each value strictly less than the previous (newest < next-newest …)
    if all(values[i] < values[i + 1] for i in range(len(values) - 1)):
        return "falling"
    if all(values[i] > values[i + 1] for i in range(len(values) - 1)):
        return "rising"
    return "stable"


# ---------------------------------------------------------------------------
# Step 3: Latest PP state per system (bulk helper)
# ---------------------------------------------------------------------------


def get_latest_pp_states(db: Session) -> dict[int, dict]:
    """Return a dict mapping system.id → latest PP snapshot fields.

    Uses PostgreSQL ``DISTINCT ON`` for an efficient single-query lookup.
    """
    sql = text(
        """
        SELECT DISTINCT ON (system_id) system_id, pp_state, pp_power, influence
        FROM pp_snapshots
        ORDER BY system_id, snapshot_time DESC
        """
    )
    rows = db.execute(sql).mappings().all()
    return {
        row["system_id"]: {
            "pp_state": row["pp_state"],
            "pp_power": row["pp_power"],
            "influence": row["influence"],
        }
        for row in rows
    }


# ---------------------------------------------------------------------------
# Distance helper
# ---------------------------------------------------------------------------


def _dist(ax: float, ay: float, az: float, bx: float, by: float, bz: float) -> float:
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)


# ---------------------------------------------------------------------------
# Step 4: Fortify scores
# ---------------------------------------------------------------------------


def compute_fortify_scores(
    faction_name: str,
    center_coords: Optional[tuple[float, float, float]],
    presence_rows: list,
    pp_states: dict[int, dict],
    db: Session,
    weights: dict[str, float],
) -> list[RecommendationItem]:
    """Score each system in the faction's current presence list for fortify urgency.

    ``presence_rows`` is a list of ``(FactionPresence, System)`` tuples.
    """
    items: list[RecommendationItem] = []

    for presence, system in presence_rows:
        pp = pp_states.get(system.id, {})
        pp_state: Optional[str] = pp.get("pp_state")
        influence: Optional[float] = pp.get("influence")

        score = 0.0
        reasons: list[str] = []

        if pp_state == "Undermined":
            score += weights["fortify_undermined"]
            reasons.append("System is Undermined")

        if pp_state == "Turmoil":
            score += weights["fortify_turmoil"]
            reasons.append("System is in Turmoil")

        if influence is not None and influence < 0.4:
            score += weights["fortify_low_influence"]
            reasons.append(f"Low faction influence ({influence * 100:.0f}%)")

        trend = get_influence_trend(system.id, db)
        if trend == "falling":
            score += weights["fortify_trend_down"]
            reasons.append("Faction influence is declining")

        if not presence.is_controlling:
            score += weights["fortify_not_controlling"]
            reasons.append("Faction does not control this system")

        sx = system.x or 0.0
        sy = system.y or 0.0
        sz = system.z or 0.0

        distance_from_center: Optional[float] = None
        if center_coords is not None:
            cx, cy, cz = center_coords
            distance_from_center = _dist(sx, sy, sz, cx, cy, cz)
            if distance_from_center < 15.0:
                score += weights["fortify_near_center"]
                reasons.append("Close to center system (<15 LY)")

        if score <= 0:
            continue

        items.append(
            RecommendationItem(
                system_name=system.name,
                system_id64=system.system_id64,
                score=score,
                type="fortify",
                reasons=reasons,
                distance_from_center=distance_from_center,
                pp_state=pp_state,
                influence=influence,
                influence_trend=trend,
            )
        )

    items.sort(key=lambda x: x.score, reverse=True)
    return items


# ---------------------------------------------------------------------------
# Step 5: Expand scores
# ---------------------------------------------------------------------------


def compute_expand_scores(
    faction_name: str,
    center_coords: Optional[tuple[float, float, float]],
    presence_rows: list,
    pp_states: dict[int, dict],
    db: Session,
    weights: dict[str, float],
    faction_allegiance: Optional[str],
) -> list[RecommendationItem]:
    """Score candidate systems for expansion.

    Candidates are systems within 30 LY of any system the faction **controls**
    that the faction is NOT already present in.
    """
    # --- Gather faction's controlling system coords & all presence system ids ---
    controlling_coords: list[tuple[float, float, float]] = []
    faction_system_ids: set[int] = set()

    for presence, system in presence_rows:
        faction_system_ids.add(system.id)
        if presence.is_controlling:
            sx = system.x or 0.0
            sy = system.y or 0.0
            sz = system.z or 0.0
            controlling_coords.append((sx, sy, sz))

    if not controlling_coords:
        # Faction controls nothing — no expansion candidates
        return []

    # --- Build bounding box to pre-filter the systems table ---
    all_x = [c[0] for c in controlling_coords]
    all_y = [c[1] for c in controlling_coords]
    all_z = [c[2] for c in controlling_coords]
    min_x, max_x = min(all_x) - 30.0, max(all_x) + 30.0
    min_y, max_y = min(all_y) - 30.0, max(all_y) + 30.0
    min_z, max_z = min(all_z) - 30.0, max(all_z) + 30.0

    candidate_systems: list[System] = (
        db.query(System)
        .filter(
            System.x.between(min_x, max_x),
            System.y.between(min_y, max_y),
            System.z.between(min_z, max_z),
            System.id.notin_(faction_system_ids),
        )
        .all()
    )

    if not candidate_systems:
        return []

    # --- Pre-fetch presence counts and allegiance info for candidates ---
    candidate_ids = [s.id for s in candidate_systems]

    # Count factions present per system (any ingestion run, distinct faction_ids)
    faction_count_sql = text(
        """
        SELECT system_id, COUNT(DISTINCT faction_id) AS n_factions
        FROM faction_presence
        WHERE system_id = ANY(:ids)
        GROUP BY system_id
        """
    )
    faction_count_rows = db.execute(
        faction_count_sql, {"ids": candidate_ids}
    ).mappings().all()
    faction_count_by_system: dict[int, int] = {
        r["system_id"]: r["n_factions"] for r in faction_count_rows
    }

    # Find systems where a faction with the same allegiance is controlling
    if faction_allegiance:
        same_allegiance_sql = text(
            """
            SELECT fp.system_id
            FROM faction_presence fp
            JOIN factions f ON f.id = fp.faction_id
            WHERE fp.system_id = ANY(:ids)
              AND fp.is_controlling = TRUE
              AND f.allegiance = :allegiance
            """
        )
        same_allegiance_rows = db.execute(
            same_allegiance_sql,
            {"ids": candidate_ids, "allegiance": faction_allegiance},
        ).mappings().all()
        same_allegiance_system_ids: set[int] = {
            r["system_id"] for r in same_allegiance_rows
        }
    else:
        same_allegiance_system_ids = set()

    # Find systems that have NO controlling faction at all
    has_controller_sql = text(
        """
        SELECT DISTINCT system_id
        FROM faction_presence
        WHERE system_id = ANY(:ids)
          AND is_controlling = TRUE
        """
    )
    has_controller_rows = db.execute(
        has_controller_sql, {"ids": candidate_ids}
    ).mappings().all()
    systems_with_controller: set[int] = {r["system_id"] for r in has_controller_rows}

    # --- Score each candidate ---
    items: list[RecommendationItem] = []

    for system in candidate_systems:
        sx = system.x or 0.0
        sy = system.y or 0.0
        sz = system.z or 0.0

        # Exact distance check: must be within 30 LY of at least one controlling system
        min_dist = min(_dist(sx, sy, sz, cx, cy, cz) for cx, cy, cz in controlling_coords)
        if min_dist > 30.0:
            continue

        pp = pp_states.get(system.id, {})
        pp_state: Optional[str] = pp.get("pp_state")
        influence: Optional[float] = pp.get("influence")

        score = 0.0
        reasons: list[str] = []

        if system.id not in systems_with_controller:
            score += weights["expand_uncontrolled"]
            reasons.append("System has no controlling faction")

        if min_dist < 20.0:
            score += weights["expand_proximity"]
            reasons.append(f"Close to controlled system ({min_dist:.1f} LY)")

        if pp_state in ("Expansion", "InPrepareRadius"):
            score += weights["expand_pp_state"]
            reasons.append(f"System is in {pp_state} state")

        if system.id not in same_allegiance_system_ids:
            score += weights["expand_allegiance_gap"]
            reasons.append("No competing same-allegiance faction controls this system")

        n_factions = faction_count_by_system.get(system.id, 0)
        if n_factions < 3:
            score += weights["expand_low_competition"]
            reasons.append(f"Low competition ({n_factions} factions present)")

        if score <= 0:
            continue

        distance_from_center: Optional[float] = None
        if center_coords is not None:
            cx, cy, cz = center_coords
            distance_from_center = _dist(sx, sy, sz, cx, cy, cz)

        trend = get_influence_trend(system.id, db)

        items.append(
            RecommendationItem(
                system_name=system.name,
                system_id64=system.system_id64,
                score=score,
                type="expand",
                reasons=reasons,
                distance_from_center=distance_from_center,
                pp_state=pp_state,
                influence=influence,
                influence_trend=trend,
            )
        )

    items.sort(key=lambda x: x.score, reverse=True)
    return items[:20]


# ---------------------------------------------------------------------------
# Step 6: Main public function
# ---------------------------------------------------------------------------


def compute_recommendations(
    faction_name: str,
    center_system_id64: Optional[int],
    db: Session,
) -> dict:
    """Return fortify and expand recommendation lists for a faction.

    Returns::

        {
            "fortify":     [RecommendationItem, ...],   # sorted by score desc, max 20
            "expand":      [RecommendationItem, ...],   # sorted by score desc, max 20
            "llm_summary": str | None,
        }
    """
    import logging
    import os

    weights = load_weights(db)
    pp_states = get_latest_pp_states(db)

    faction = db.query(Faction).filter(Faction.name == faction_name).first()
    if not faction:
        return {"fortify": [], "expand": [], "llm_summary": None}

    # Deduplicated presence rows: one row per system, preferring is_controlling=True
    presence_rows = (
        db.query(FactionPresence, System)
        .join(System, FactionPresence.system_id == System.id)
        .filter(FactionPresence.faction_id == faction.id)
        .distinct(FactionPresence.system_id)
        .order_by(FactionPresence.system_id, FactionPresence.is_controlling.desc())
        .all()
    )

    # Resolve center system coordinates and name
    center_coords: Optional[tuple[float, float, float]] = None
    center_name: Optional[str] = None
    if center_system_id64 is not None:
        center_sys = (
            db.query(System)
            .filter(System.system_id64 == center_system_id64)
            .first()
        )
        if center_sys is not None:
            center_coords = (
                center_sys.x or 0.0,
                center_sys.y or 0.0,
                center_sys.z or 0.0,
            )
            center_name = center_sys.name

    fortify = compute_fortify_scores(
        faction_name, center_coords, presence_rows, pp_states, db, weights
    )
    expand = compute_expand_scores(
        faction_name,
        center_coords,
        presence_rows,
        pp_states,
        db,
        weights,
        faction.allegiance,
    )

    result: dict = {
        "fortify": fortify[:20],
        "expand": expand[:20],
        "llm_summary": None,
    }

    if os.getenv("LLM_ENABLED", "false").lower() == "true":
        try:
            from ai.factory import get_provider
            provider = get_provider()
            fortify_dicts = [item.model_dump() for item in fortify[:5]]
            expand_dicts = [item.model_dump() for item in expand[:5]]
            result["llm_summary"] = provider.summarize_recommendations(
                faction_name, center_name, fortify_dicts, expand_dicts
            )
        except Exception as exc:
            logging.getLogger(__name__).warning("LLM summary failed: %s", exc)

    return result
