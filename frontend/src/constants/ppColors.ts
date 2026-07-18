/** Map Power Play 2.0 state strings to display colors.
 *
 * Actual PP 2.0 states as returned by Spansh API (confirmed July 2026):
 *   Stronghold   — maximally defended (best possible state for controlling power)
 *   Fortified    — reinforced above threshold
 *   Exploited    — basic controlled state, actively being worked
 *   Unoccupied   — PP bubble presence but no controlling power (expansion target)
 *
 * Legacy / extra states kept for forward compatibility with possible future states.
 */
export function ppStateColor(state: string | null | undefined): string {
  switch (state) {
    case "Stronghold":       return "#00E5CC";   // teal — max defense
    case "Fortified":        return "#4AD94A";   // green — reinforced
    case "Exploited":        return "#8899AA";   // blue-grey — basic controlled
    case "Unoccupied":       return "#7c5cd8";   // purple — no controller, expand target
    // Legacy / forward-compat states
    case "Turmoil":          return "#FF4500";
    case "Undermined":       return "#D94A4A";
    case "Contested":        return "#D9A84A";
    case "Expansion":        return "#4A90D9";
    case "InPrepareRadius":  return "#B06AF0";
    case "Prepared":         return "#C890FF";
    case "HomeSystem":       return "#FFD700";
    default:                 return "#555566";
  }
}

export const PP_STATE_LABELS: Record<string, string> = {
  Stronghold:      "Stronghold",
  Fortified:       "Fortified",
  Exploited:       "Exploited",
  Unoccupied:      "Unoccupied",
  // Legacy
  Turmoil:         "Turmoil",
  Undermined:      "Undermined",
  Contested:       "Contested",
  Expansion:       "Expansion",
  InPrepareRadius: "Prepare Radius",
  Prepared:        "Prepared",
  HomeSystem:      "Home System",
};

/** Ordered list of active PP 2.0 states for legend rendering (confirmed live states first). */
export const PP_STATES_ORDERED = [
  "Stronghold", "Fortified", "Exploited", "Unoccupied",
] as const;
