/** Systems API client. */

export interface SystemSearchResult {
  system_id64: number;
  name: string;
  x: number | null;
  y: number | null;
  z: number | null;
}

export interface SystemHistoryPoint {
  snapshot_time: string;
  pp_state: string | null;
  pp_power: string | null;
  influence: number | null;
}

export async function searchSystems(q: string): Promise<SystemSearchResult[]> {
  const res = await fetch(
    `/api/systems/search?q=${encodeURIComponent(q)}`
  );
  if (!res.ok) throw new Error(`System search failed (${res.status})`);
  return res.json() as Promise<SystemSearchResult[]>;
}

export async function getSystemHistory(
  systemId64: number
): Promise<SystemHistoryPoint[]> {
  const res = await fetch(`/api/systems/${systemId64}/history`);
  if (!res.ok) throw new Error(`System history failed (${res.status})`);
  return res.json() as Promise<SystemHistoryPoint[]>;
}
