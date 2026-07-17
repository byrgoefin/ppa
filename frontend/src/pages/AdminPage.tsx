/**
 * Admin page — login form + admin panel stub.
 * Full implementation in Sub-Task 10.
 */

import React, { useState } from "react";
import { adminLogin, setAdminToken, clearAdminToken, getAdminToken } from "../api/admin";

interface Props {
  onClose: () => void;
}

export default function AdminPage({ onClose }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loggedIn, setLoggedIn] = useState<boolean>(!!getAdminToken());

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await adminLogin(email, password);
      setAdminToken(resp.access_token);
      setLoggedIn(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    clearAdminToken();
    setLoggedIn(false);
  }

  const panelStyle: React.CSSProperties = {
    maxWidth: 480,
    margin: "64px auto",
    padding: 32,
    border: "1px solid #e5e7eb",
    borderRadius: 8,
    background: "#f7f8fa",
    fontFamily: '-apple-system, "Segoe UI", system-ui, sans-serif',
  };

  return (
    <div style={{ paddingTop: 44, background: "#fff", minHeight: "100vh" }}>
      {/* Minimal top bar */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: 44,
          background: "#fff",
          borderBottom: "1px solid #e5e7eb",
          display: "flex",
          alignItems: "center",
          padding: "0 16px",
          gap: 12,
          zIndex: 1000,
          fontFamily: '-apple-system, "Segoe UI", system-ui, sans-serif',
        }}
      >
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 14,
            color: "#57606a",
          }}
        >
          ← Back
        </button>
        <span style={{ fontWeight: 600, fontSize: 14 }}>Admin Panel</span>
      </div>

      {!loggedIn ? (
        <div style={panelStyle}>
          <h2 style={{ margin: "0 0 24px", fontSize: 18, fontWeight: 600 }}>
            Admin Login
          </h2>
          <form onSubmit={(e) => { void handleLogin(e); }}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  fontSize: 14,
                  border: "1px solid #e5e7eb",
                  borderRadius: 5,
                  boxSizing: "border-box",
                }}
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: 13, marginBottom: 4 }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  fontSize: 14,
                  border: "1px solid #e5e7eb",
                  borderRadius: 5,
                  boxSizing: "border-box",
                }}
              />
            </div>
            {error && (
              <p style={{ color: "#D94A4A", fontSize: 13, marginBottom: 12 }}>
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                padding: "10px",
                fontSize: 14,
                fontWeight: 600,
                background: "#3b82d4",
                color: "#fff",
                border: "none",
                borderRadius: 5,
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Logging in…" : "Login"}
            </button>
          </form>
        </div>
      ) : (
        <div style={panelStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Admin Panel</h2>
            <button
              onClick={handleLogout}
              style={{
                fontSize: 13,
                padding: "5px 12px",
                border: "1px solid #e5e7eb",
                borderRadius: 5,
                cursor: "pointer",
                background: "none",
                color: "#57606a",
              }}
            >
              Logout
            </button>
          </div>
          <p style={{ color: "#57606a", fontSize: 14 }}>
            Ingestion controls, run history, and scoring weight editor will be
            implemented in Sub-Task 10.
          </p>
        </div>
      )}
    </div>
  );
}
