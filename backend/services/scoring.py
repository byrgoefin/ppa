"""Power Play 2.0 recommendation scoring engine.

Scores systems for fortify urgency and expansion attractiveness based on
real Power Play metrics from the Spansh dump:

  - Reinforcement: commodity deliveries supporting the system
  - Undermining:   enemy deliveries attacking the system
  - Power State:   Stronghold | Fortified | Exploited | Turmoil | Undermined |
                   Contested | Expansion | InPrepareRadius | Prepared | HomeSystem
  - Undermine ratio: undermining / reinforcement — higher = more threatened

PP 2.0 state semantics:
  Stronghold    — maximum defense (high reinforcement cap); skip fortify (already excellent)
  Fortified     — above reinforcement threshold; healthy but can improve
  Exploited     — base controlled state, no special reinforcement; monitor ratio
  Turmoil       — critical: system will be lost if not rescued
  Undermined    — actively being undermined, not yet in Turmoil
  Contested     — multiple powers fighting for control
  Expansion     — power expanding into this system
  InPrepareRadius — in range of a prepare-phase system
  Prepared      — system prepared; actively becoming expansion target
  HomeSystem    — power capital; should never need fortify

Weights are loaded from the admin_settings table with hard-coded defaults.
"""

from __future__ import annotations

import math
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.models import AdminSetting, PPSystem, PPSystemSnapshot
from models.schemas import RecommendationItem

# ---------------------------------------------------------------------------
# Default scoring weights
# ---------------------------------------------------------------------------

DEFAULTS: dict[str, float] = {
    # ── Fortify weights ──────────────────────────────────────────────────────
    "fortify_turmoil":           70.0,   # system in Turmoil — will be lost very soon
    "fortify_undermined":        55.0,   # system is Undermined (not yet Turmoil)
    "fortify_contested":         35.0,   # system is Contested by another power
    "fortify_exploited_ratio":   30.0,   # Exploited system with high undermine ratio
    "fortify_high_ratio":        40.0,   # undermine ratio > 0.5 (any state)
    "fortify_trend_worsening":   20.0,   # undermine ratio rising across snapshots
    "fortify_near_center":       10.0,   # within 15 LY of the center system
    # Stronghold systems are already maximally defended — no fortify bonus
    # (we actively suppress them from fortify list via the engine)

    # ── Expand weights ───────────────────────────────────────────────────────
    "expand_prepared":           60.0,   # Prepared state — actively becoming expansion target
    "expand_in_prepare":         50.0,   # InPrepareRadius — prime expansion target
    "expand_expansion_state":    40.0,   # Expansion state — actively expanding
    "expand_no_controller":      30.0,   # no power currently controls the system
    "expand_proximity":          20.0,   # within 20 LY of a power-controlled system
    "expand_allegiance_match":   15.0,   # system allegiance matches the power
}

# Map powers to their typical allegiance (for expand allegiance bonus).
# Includes all PP 2.0 powers as of 2024-2025.
POWER_ALLEGIANCE: dict[str, str] = {
    # Empire
    "Arissa Lavigny-Duval": "Empire",
    "Aisling Duval":        "Empire",
    "Zemina Torval":        "Empire",
    "Denton Patreus":       "Empire",
    # Federation
    "Zachary Hudson":       "Federation",
    "Felicia Winters":      "Federation",
    "Jerome Archer":        "Federation",
    # Alliance
    "Edmund Mahon":         "Alliance",
    "Nakato Kaine":         "Alliance",
    # Independent
    "Pranav Antal":         "Independent",
    "Li Yong-Rui":          "Independent",
    "Archon Delaine":       "Independent",
    "Yuri Grom":            "Independent",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_weights(db: Session) -> dict[str, float]:
    rows = db.query(AdminSetting).all()
    weights = dict(DEFAULTS)
    for row in rows:
        if row.key in weights:
            try:
                weights[row.key] = float(row.value)
            except (ValueError, TypeError):
                pass
    return weights


def _dist(ax: float, ay: float, az: float, bx: float, by: float, bz: float) -> float:
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)


def get_latest_snapshots(db: Session) -> dict[int, dict]:
    """Return latest PP snapshot per pp_systems.id using DISTINCT ON."""
    sql = text("""
        SELECT DISTINCT ON (system_id)
               system_id, power, power_state,
               reinforcement, undermining, control_progress, snapshot_time
        FROM pp_system_snapshots
        ORDER BY system_id, snapshot_time DESC
    """)
    rows = db.execute(sql).mappings().all()
    return {
        row["system_id"]: dict(row)
        for row in rows
    }


def get_undermine_trend(system_id: int, db: Session) -> str:
    """Compare the last 3 undermine ratios for a system.

    Returns 'worsening', 'improving', 'stable', or 'unknown'.
    """
    rows = db.execute(
        text("""
            SELECT reinforcement, undermining
            FROM pp_system_snapshots
            WHERE system_id = :sid
              AND reinforcement IS NOT NULL
              AND undermining   IS NOT NULL
              AND reinforcement > 0
            ORDER BY snapshot_time DESC
            LIMIT 3
        """),
        {"sid": system_id},
    ).all()

    if len(rows) < 2:
        return "unknown"

    ratios = [r.undermining / r.reinforcement for r in rows]  # newest first
    if all(ratios[i] > ratios[i + 1] for i in range(len(ratios) - 1)):
        return "worsening"
    if all(ratios[i] < ratios[i + 1] for i in range(len(ratios) - 1)):
        return "improving"
    return "stable"


# ---------------------------------------------------------------------------
# Fortify scoring
# ---------------------------------------------------------------------------


def compute_fortify_scores(
    power_name: str,
    center_coords: Optional[tuple[float, float, float]],
    power_systems: list[PPSystem],
    snapshots: dict[int, dict],
    db: Session,
    weights: dict[str, float],
) -> list[RecommendationItem]:
    items: list[RecommendationItem] = []

    for system in power_systems:
        snap = snapshots.get(system.id, {})
        power_state: Optional[str] = snap.get("power_state")
        reinforcement: Optional[int] = snap.get("reinforcement")
        undermining: Optional[int] = snap.get("undermining")

        undermine_ratio: Optional[float] = None
        if reinforcement and reinforcement > 0 and undermining is not None:
            undermine_ratio = undermining / reinforcement

        score = 0.0
        reasons: list[str] = []

        # Stronghold systems are already maximally defended — skip them entirely
        # so commanders focus effort where it's actually needed.
        if power_state == "Stronghold":
            continue

        if power_state == "Turmoil":
            score += weights["fortify_turmoil"]
            reasons.append("System in Turmoil — at risk of being lost!")

        elif power_state == "Undermined":
            score += weights["fortify_undermined"]
            reasons.append("System is Undermined")

        elif power_state == "Contested":
            score += weights["fortify_contested"]
            reasons.append("System is Contested by another power")

        elif power_state == "Exploited" and undermine_ratio is not None and undermine_ratio > 0.3:
            score += weights["fortify_exploited_ratio"]
            reasons.append(f"Exploited system under undermining pressure ({undermine_ratio:.0%})")

        if undermine_ratio is not None and undermine_ratio > 0.5:
            score += weights["fortify_high_ratio"]
            reasons.append(f"High undermine ratio ({undermine_ratio:.0%})")

        trend = get_undermine_trend(system.id, db)
        if trend == "worsening":
            score += weights["fortify_trend_worsening"]
            reasons.append("Undermining pressure is increasing")

        sx, sy, sz = system.x or 0.0, system.y or 0.0, system.z or 0.0
        distance_from_center: Optional[float] = None
        if center_coords is not None:
            cx, cy, cz = center_coords
            distance_from_center = _dist(sx, sy, sz, cx, cy, cz)
            if distance_from_center < 15.0:
                score += weights["fortify_near_center"]
                reasons.append(f"Close to center system ({distance_from_center:.1f} LY)")

        if score <= 0:
            continue

        items.append(RecommendationItem(
            system_id64=system.system_id64,
            system_name=system.name,
            score=score,
            type="fortify",
            reasons=reasons,
            power_state=power_state,
            reinforcement=reinforcement,
            undermining=undermining,
            undermine_ratio=undermine_ratio,
            distance_from_center=distance_from_center,
            threat_trend=trend,
        ))

    items.sort(key=lambda x: x.score, reverse=True)
    return items


# ---------------------------------------------------------------------------
# Expand scoring
# ---------------------------------------------------------------------------


def compute_expand_scores(
    power_name: str,
    center_coords: Optional[tuple[float, float, float]],
    power_systems: list[PPSystem],
    snapshots: dict[int, dict],
    db: Session,
    weights: dict[str, float],
) -> list[RecommendationItem]:
    """Score nearby systems not yet controlled by this power for expansion."""

    if not power_systems:
        return []

    power_coords = [(s.x or 0.0, s.y or 0.0, s.z or 0.0) for s in power_systems]
    power_system_ids = {s.id for s in power_systems}
    power_allegiance = POWER_ALLEGIANCE.get(power_name)

    # Bounding box pre-filter: 30 LY around any power system
    all_x = [c[0] for c in power_coords]
    all_y = [c[1] for c in power_coords]
    all_z = [c[2] for c in power_coords]
    min_x, max_x = min(all_x) - 30.0, max(all_x) + 30.0
    min_y, max_y = min(all_y) - 30.0, max(all_y) + 30.0
    min_z, max_z = min(all_z) - 30.0, max(all_z) + 30.0

    candidates: list[PPSystem] = db.query(PPSystem).filter(
        PPSystem.x.between(min_x, max_x),
        PPSystem.y.between(min_y, max_y),
        PPSystem.z.between(min_z, max_z),
        PPSystem.id.notin_(power_system_ids),
    ).all()

    items: list[RecommendationItem] = []

    for system in candidates:
        sx, sy, sz = system.x or 0.0, system.y or 0.0, system.z or 0.0
        min_dist = min(_dist(sx, sy, sz, cx, cy, cz) for cx, cy, cz in power_coords)
        if min_dist > 30.0:
            continue

        snap = snapshots.get(system.id, {})
        power_state: Optional[str] = snap.get("power_state")
        current_power: Optional[str] = snap.get("power")

        score = 0.0
        reasons: list[str] = []

        if power_state == "Prepared":
            score += weights["expand_prepared"]
            reasons.append("System is Prepared — becoming expansion target")

        elif power_state == "InPrepareRadius":
            score += weights["expand_in_prepare"]
            reasons.append("System is in prepare radius — prime expansion target")

        elif power_state == "Expansion":
            score += weights["expand_expansion_state"]
            reasons.append("System is actively in Expansion state")

        if not current_power:
            score += weights["expand_no_controller"]
            reasons.append("System has no controlling power")

        if min_dist < 20.0:
            score += weights["expand_proximity"]
            reasons.append(f"Close to controlled system ({min_dist:.1f} LY)")

        if power_allegiance and system.allegiance == power_allegiance:
            score += weights["expand_allegiance_match"]
            reasons.append(f"{system.allegiance} allegiance matches power")

        if score <= 0:
            continue

        distance_from_center: Optional[float] = None
        if center_coords is not None:
            cx, cy, cz = center_coords
            distance_from_center = _dist(sx, sy, sz, cx, cy, cz)

        items.append(RecommendationItem(
            system_id64=system.system_id64,
            system_name=system.name,
            score=score,
            type="expand",
            reasons=reasons,
            power_state=power_state,
            distance_from_center=distance_from_center,
            threat_trend="unknown",
        ))

    items.sort(key=lambda x: x.score, reverse=True)
    return items[:20]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_recommendations(
    power_name: str,
    center_system_id64: Optional[int],
    db: Session,
) -> dict:
    import logging
    import os

    weights = load_weights(db)
    snapshots = get_latest_snapshots(db)

    # All systems currently under this power (latest snapshot says power == power_name)
    powered_system_ids = {
        sid for sid, snap in snapshots.items()
        if snap.get("power") == power_name
    }
    if not powered_system_ids:
        return {"fortify": [], "expand": [], "llm_summary": None}

    power_systems = db.query(PPSystem).filter(PPSystem.id.in_(powered_system_ids)).all()

    center_coords: Optional[tuple[float, float, float]] = None
    center_name: Optional[str] = None
    if center_system_id64 is not None:
        center_sys = db.query(PPSystem).filter(PPSystem.system_id64 == center_system_id64).first()
        if center_sys:
            center_coords = (center_sys.x or 0.0, center_sys.y or 0.0, center_sys.z or 0.0)
            center_name = center_sys.name

    fortify = compute_fortify_scores(power_name, center_coords, power_systems, snapshots, db, weights)
    expand = compute_expand_scores(power_name, center_coords, power_systems, snapshots, db, weights)

    result: dict = {
        "fortify": fortify[:20],
        "expand":  expand[:20],
        "llm_summary": None,
    }

    if os.getenv("LLM_ENABLED", "false").lower() == "true":
        try:
            from ai.factory import get_provider
            provider = get_provider()
            result["llm_summary"] = provider.summarize_recommendations(
                power_name, center_name,
                [i.model_dump() for i in fortify[:5]],
                [i.model_dump() for i in expand[:5]],
            )
        except Exception as exc:
            logging.getLogger(__name__).warning("LLM summary failed: %s", exc)

    return result
