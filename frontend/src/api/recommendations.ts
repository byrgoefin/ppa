/** Recommendations API client. */

export interface RecommendationItem {
  system_id64: number;
  system_name: string;
  score: number;
  type: "fortify" | "expand";
  reasons: string[];
  power_state: string | null;
  reinforcement: number | null;
  undermining: number | null;
  undermine_ratio: number | null;
  /** Normalized 0.0–1.0+ progress toward next state; <0 = failing now; ≥1 = upgrade ready */
  control_progress: number | null;
  /** Estimated days until state downgrade; 0 = failing now; null = not at risk */
  days_to_failure: number | null;
  distance_from_center: number | null;
  threat_trend: "worsening" | "improving" | "stable" | "unknown";
}

export interface RecommendationsResponse {
  fortify: RecommendationItem[];
  expand: RecommendationItem[];
  llm_summary: string | null;
}

export async function getRecommendations(
  powerName: string,
  centerSystemId64?: number,
): Promise<RecommendationsResponse> {
  const params = new URLSearchParams();
  if (centerSystemId64 != null) params.set("center_id", String(centerSystemId64));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(
    `/api/powers/${encodeURIComponent(powerName)}/recommendations${qs}`
  );
  if (!res.ok) throw new Error(`Get recommendations failed (${res.status})`);
  return res.json() as Promise<RecommendationsResponse>;
}
