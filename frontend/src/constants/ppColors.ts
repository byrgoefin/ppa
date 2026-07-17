/**
 * PP State color constants — shared across Table, 2D Map, and 3D Map views.
 *
 * Values match the design spec from the plan:
 *   Fortified  = #4AD94A (green)
 *   Undermined = #D94A4A (red)
 *   Turmoil    = #FF8C00 (orange)
 *   Expansion  = #4A90D9 (blue)
 *   Contested  = #D9D94A (yellow)
 *   default    = #999999 (grey)
 */

export const PP_STATE_COLORS: Record<string, string> = {
  Fortified: "#4AD94A",
  Undermined: "#D94A4A",
  Turmoil: "#FF8C00",
  Expansion: "#4A90D9",
  Contested: "#D9D94A",
  HomeSystem: "#7c5cd8",
  Prepared: "#3b82d4",
  InPrepareRadius: "#3b82d4",
  Exploited: "#aaaaaa",
};

/** Returns the color for a given PP state string, falling back to grey. */
export function ppStateColor(state: string | null | undefined): string {
  if (!state) return "#999999";
  return PP_STATE_COLORS[state] ?? "#999999";
}
