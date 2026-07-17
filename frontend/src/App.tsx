import React, { useState } from "react";
import TableView from "./pages/TableView";
import Map2DView from "./pages/Map2DView";
import Map3DView from "./pages/Map3DView";
import AdminPage from "./pages/AdminPage";

type Tab = "table" | "map2d" | "map3d";

const TAB_LABELS: Record<Tab, string> = {
  table: "Table",
  map2d: "2D Map",
  map3d: "3D Map",
};

const tabBarStyle: React.CSSProperties = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  height: 44,
  background: "#fff",
  borderBottom: "1px solid #e5e7eb",
  display: "flex",
  alignItems: "center",
  gap: 0,
  padding: "0 16px",
  zIndex: 1000,
  fontFamily: '-apple-system, "Segoe UI", system-ui, sans-serif',
};

function tabBtnStyle(active: boolean): React.CSSProperties {
  return {
    padding: "0 18px",
    height: 44,
    fontSize: 14,
    fontWeight: active ? 600 : 400,
    color: active ? "#3b82d4" : "#57606a",
    background: "none",
    border: "none",
    borderBottom: active ? "2px solid #3b82d4" : "2px solid transparent",
    cursor: "pointer",
    outline: "none",
  };
}

export default function App() {
  const [tab, setTab] = useState<Tab>("table");
  const [showAdmin, setShowAdmin] = useState(false);

  if (showAdmin) {
    return <AdminPage onClose={() => setShowAdmin(false)} />;
  }

  return (
    <div style={{ fontFamily: '-apple-system, "Segoe UI", system-ui, sans-serif' }}>
      {/* Tab bar */}
      <div style={tabBarStyle}>
        {(["table", "map2d", "map3d"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)} style={tabBtnStyle(tab === t)}>
            {TAB_LABELS[t]}
          </button>
        ))}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Admin icon — top-right */}
        <button
          onClick={() => setShowAdmin(true)}
          title="Admin panel"
          style={{
            padding: "5px 12px",
            fontSize: 13,
            color: "#57606a",
            background: "none",
            border: "1px solid #e5e7eb",
            borderRadius: 5,
            cursor: "pointer",
          }}
        >
          ⚙ Admin
        </button>
      </div>

      {/* Page content — offset by tab bar height */}
      <div style={{ paddingTop: 44 }}>
        {tab === "table" && <TableView />}
        {tab === "map2d" && <Map2DView />}
        {tab === "map3d" && <Map3DView />}
      </div>
    </div>
  );
}
