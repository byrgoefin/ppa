import React, { useState, useEffect, useMemo } from "react";
import { getPowerSystems, PPSystemEntry } from "../api/powers";
import { getRecommendations, RecommendationsResponse } from "../api/recommendations";
import { useSelectionState } from "../hooks/useSelectionState";
import { ppStateColor, PP_STATE_LABELS } from "../constants/ppColors";
import PowerSelector from "../components/PowerSelector";
import CenterSystemSelector from "../components/CenterSystemSelector";
import RecommendationPanel from "../components/RecommendationPanel";

type SortKey = keyof PPSystemEntry | "recommendation";
type SortDir = "asc" | "desc";

function cmp(a: unknown, b: unknown, dir: SortDir): number {
  const f = dir === "asc" ? 1 : -1;
  if (a == null && b == null) return 0;
  if (a == null) return f;
  if (b == null) return -f;
  if (typeof a === "string" && typeof b === "string") return f * a.localeCompare(b);
  if (typeof a === "number" && typeof b === "number") return f * (a - b);
  return 0;
}

function PPBadge({ state }: { state: string | null }) {
  if (!state) return <span style={{ color: "#999" }}>—</span>;
  return (
    <span style={{ background: ppStateColor(state), color: "#fff", borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600 }}>
      {PP_STATE_LABELS[state] ?? state}
    </span>
  );
}

function RecoBadge({ type }: { type: "fortify" | "expand" | null }) {
  if (!type) return null;
  return (
    <span style={{ background: type === "fortify" ? "#D94A4A" : "#3b82d4", color: "#fff", borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 600 }}>
      {type === "fortify" ? "Fortify" : "Expand"}
    </span>
  );
}

function ThreatArrow({ trend }: { trend: string }) {
  if (trend === "worsening") return <span style={{ color: "#D94A4A" }} title="Undermining increasing">↑</span>;
  if (trend === "improving") return <span style={{ color: "#4AD94A" }} title="Undermining decreasing">↓</span>;
  return <span style={{ color: "#999" }}>—</span>;
}

function Th({ col, label, sortKey, sortDir, onSort, width }: {
  col: string; label: string; sortKey: string; sortDir: SortDir;
  onSort: (k: string) => void; width?: number;
}) {
  const active = col === sortKey;
  return (
    <th onClick={() => onSort(col)} style={{ padding: "10px 12px", textAlign: "left", fontSize: 12, fontWeight: 700, color: "#57606a", textTransform: "uppercase", letterSpacing: "0.04em", cursor: "pointer", whiteSpace: "nowrap", background: "#f7f8fa", borderBottom: "2px solid #e5e7eb", width }}>
      {label}
      <span style={{ marginLeft: 4, color: active ? "#1f2328" : "#ccc" }}>{active ? (sortDir === "asc" ? "↑" : "↓") : "↕"}</span>
    </th>
  );
}

export default function TableView() {
  const { powerName, centerSystem, setPower, setCenter } = useSelectionState();

  const [systems, setSystems] = useState<PPSystemEntry[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [loadingSystems, setLoadingSystems] = useState(false);
  const [loadingRecos, setLoadingRecos] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<string>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const fortifySet = useMemo(() => new Set((recommendations?.fortify ?? []).map((r) => r.system_name)), [recommendations]);
  const expandSet  = useMemo(() => new Set((recommendations?.expand  ?? []).map((r) => r.system_name)), [recommendations]);

  function getRecoType(name: string): "fortify" | "expand" | null {
    if (fortifySet.has(name)) return "fortify";
    if (expandSet.has(name))  return "expand";
    return null;
  }

  useEffect(() => {
    if (!powerName) { setSystems([]); setRecommendations(null); return; }
    setLoadingSystems(true);
    setError(null);
    getPowerSystems(powerName, centerSystem?.id)
      .then(setSystems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoadingSystems(false));
  }, [powerName, centerSystem?.id]);

  useEffect(() => {
    if (!powerName) { setRecommendations(null); return; }
    setLoadingRecos(true);
    getRecommendations(powerName, centerSystem?.id)
      .then(setRecommendations)
      .catch(() => setRecommendations(null))
      .finally(() => setLoadingRecos(false));
  }, [powerName, centerSystem?.id]);

  useEffect(() => {
    setSortKey(centerSystem ? "distance_from_center" : "name");
    setSortDir("asc");
  }, [centerSystem?.id]);

  function handleSort(col: string) {
    if (col === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(col); setSortDir("asc"); }
  }

  const sorted = useMemo(() => [...systems].sort((a, b) => {
    if (sortKey === "recommendation") {
      return cmp(getRecoType(a.name), getRecoType(b.name), sortDir);
    }
    return cmp((a as Record<string, unknown>)[sortKey], (b as Record<string, unknown>)[sortKey], sortDir);
  }), [systems, sortKey, sortDir, fortifySet, expandSet]);

  const showDistance = !!centerSystem;

  return (
    <div style={{ padding: "20px 24px", fontFamily: '-apple-system,"Segoe UI",system-ui,sans-serif', color: "#1f2328" }}>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", marginBottom: 16 }}>
        <PowerSelector value={powerName} onChange={setPower} />
        <CenterSystemSelector value={centerSystem} onChange={setCenter} />
        {loadingSystems && <span style={{ fontSize: 13, color: "#57606a" }}>Loading…</span>}
        {error && <span style={{ fontSize: 13, color: "#D94A4A" }}>{error}</span>}
      </div>

      <RecommendationPanel recommendations={recommendations} loading={loadingRecos} />

      {!powerName && (
        <p style={{ color: "#57606a", fontSize: 14, marginTop: 24 }}>Search for a Power above to populate the table.</p>
      )}
      {powerName && !loadingSystems && systems.length === 0 && (
        <p style={{ color: "#57606a", fontSize: 14, marginTop: 8 }}>No systems found. Run a Spansh PP ingest first.</p>
      )}

      {systems.length > 0 && (
        <div style={{ overflowX: "auto", borderRadius: 8, border: "1px solid #e5e7eb" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                <Th col="name"             label="System"         sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                <Th col="power_state"      label="PP State"       sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
                <Th col="reinforcement"    label="Reinforcement"  sortKey={sortKey} sortDir={sortDir} onSort={handleSort} width={120} />
                <Th col="undermining"      label="Undermining"    sortKey={sortKey} sortDir={sortDir} onSort={handleSort} width={110} />
                <Th col="undermine_ratio"  label="Threat %"       sortKey={sortKey} sortDir={sortDir} onSort={handleSort} width={90} />
                <Th col="undermine_ratio"  label="Trend"          sortKey={sortKey} sortDir={sortDir} onSort={handleSort} width={65} />
                {showDistance && <Th col="distance_from_center" label="Distance (LY)" sortKey={sortKey} sortDir={sortDir} onSort={handleSort} width={120} />}
                <Th col="recommendation"   label="Action"         sortKey={sortKey} sortDir={sortDir} onSort={handleSort} width={100} />
              </tr>
            </thead>
            <tbody>
              {sorted.map((sys, i) => {
                const reco = getRecoType(sys.name);
                const recoItem = reco === "fortify"
                  ? recommendations?.fortify.find((r) => r.system_name === sys.name)
                  : reco === "expand"
                  ? recommendations?.expand.find((r) => r.system_name === sys.name)
                  : null;
                return (
                  <tr key={sys.system_id64} style={{ background: i % 2 === 0 ? "#fff" : "#f7f8fa" }}>
                    <td style={{ padding: "9px 12px", fontWeight: 500 }}>
                      <a href={`https://www.edsm.net/en/system/id/-/name/${encodeURIComponent(sys.name)}`}
                        target="_blank" rel="noreferrer"
                        style={{ color: "#3b82d4", textDecoration: "none" }}>
                        {sys.name}
                      </a>
                    </td>
                    <td style={{ padding: "9px 12px" }}><PPBadge state={sys.power_state} /></td>
                    <td style={{ padding: "9px 12px", textAlign: "right" }}>
                      {sys.reinforcement != null ? sys.reinforcement.toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "9px 12px", textAlign: "right", color: sys.undermining ? "#D94A4A" : undefined }}>
                      {sys.undermining != null ? sys.undermining.toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "9px 12px", textAlign: "right" }}>
                      {sys.undermine_ratio != null ? `${(sys.undermine_ratio * 100).toFixed(0)}%` : "—"}
                    </td>
                    <td style={{ padding: "9px 12px", textAlign: "center" }}>
                      <ThreatArrow trend={recoItem?.threat_trend ?? "unknown"} />
                    </td>
                    {showDistance && (
                      <td style={{ padding: "9px 12px", textAlign: "right" }}>
                        {sys.distance_from_center != null ? `${sys.distance_from_center.toFixed(1)} LY` : "—"}
                      </td>
                    )}
                    <td style={{ padding: "9px 12px" }}><RecoBadge type={reco} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div style={{ padding: "8px 12px", fontSize: 12, color: "#57606a", borderTop: "1px solid #e5e7eb", background: "#f7f8fa" }}>
            {sorted.length} system{sorted.length !== 1 ? "s" : ""}
            {powerName && ` · ${powerName}`}
            {centerSystem && ` · centered on ${centerSystem.name}`}
          </div>
        </div>
      )}
    </div>
  );
}
