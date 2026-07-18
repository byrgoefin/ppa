/** Map Power Play state strings to display colors. */
export function ppStateColor(state: string | null | undefined): string {
  switch (state) {
    case "Fortified":        return "#4AD94A";
    case "Undermined":       return "#D94A4A";
    case "Turmoil":          return "#FF4500";
    case "Expansion":        return "#4A90D9";
    case "InPrepareRadius":  return "#7c5cd8";
    case "Contested":        return "#D9A84A";
    case "HomeSystem":       return "#FFD700";
    case "Exploited":        return "#888";
    default:                 return "#888";
  }
}

export const PP_STATE_LABELS: Record<string, string> = {
  Fortified:       "Fortified",
  Undermined:      "Undermined",
  Turmoil:         "Turmoil",
  Expansion:       "Expansion",
  InPrepareRadius: "Prepare Radius",
  Contested:       "Contested",
  HomeSystem:      "Home System",
  Exploited:       "Exploited",
};
