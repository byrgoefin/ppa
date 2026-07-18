/** Map Power Play 2.0 state strings to display colors.
 *
 * PP 2.0 states:
 *   Stronghold       — heavily reinforced, locked in (best possible state)
 *   Fortified        — reinforced above threshold
 *   Exploited        — basic controlled system, no special reinforcement
 *   Turmoil          — critical undermining, system at risk of being lost
 *   Contested        — multiple powers vying for control
 *   Expansion        — power is actively expanding into this system
 *   InPrepareRadius  — within prepare radius, candidate for expansion
 *   Prepared         — system being prepared for expansion (pledge trigger)
 *   HomeSystem       — power's home / capital system
 */
export function ppStateColor(state: string | null | undefined): string {
  switch (state) {
    case "Stronghold":       return "#00E5CC";   // bright teal — max defense
    case "Fortified":        return "#4AD94A";   // green — reinforced
    case "Exploited":        return "#8899AA";   // blue-grey — base controlled
    case "Turmoil":          return "#FF4500";   // red-orange — at risk of loss
    case "Undermined":       return "#D94A4A";   // red — being undermined
    case "Contested":        return "#D9A84A";   // amber — contested
    case "Expansion":        return "#4A90D9";   // blue — expansion
    case "InPrepareRadius":  return "#7c5cd8";   // purple — prepare radius
    case "Prepared":         return "#B06AF0";   // light purple — prepared
    case "HomeSystem":       return "#FFD700";   // gold — home system
    default:                 return "#555566";
  }
}

export const PP_STATE_LABELS: Record<string, string> = {
  Stronghold:      "Stronghold",
  Fortified:       "Fortified",
  Exploited:       "Exploited",
  Turmoil:         "Turmoil",
  Undermined:      "Undermined",
  Contested:       "Contested",
  Expansion:       "Expansion",
  InPrepareRadius: "Prepare Radius",
  Prepared:        "Prepared",
  HomeSystem:      "Home System",
};

/** Ordered list of all PP 2.0 states for legend rendering. */
export const PP_STATES_ORDERED = [
  "Stronghold", "Fortified", "Exploited",
  "Turmoil", "Undermined", "Contested",
  "Expansion", "InPrepareRadius", "Prepared",
  "HomeSystem",
] as const;
