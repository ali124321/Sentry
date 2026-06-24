"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthContext";
import { formatDistanceToNow } from "date-fns";

interface SecretAlert { id: number; secret_type: string; secret_type_display: string; tool: string; filename: string; line_number: number; validity: string; push_protection_bypassed: boolean; created_at: string; state: string; }

const VALIDITY_COLORS: Record<string, string> = { active: "#f87171", inactive: "#64748b", unknown: "#fbbf24" };

export default function SecretAlertFeed({ repositoryId }: { repositoryId: number }) {
  const { token } = useAuth();
  const [alerts, setAlerts] = useState<SecretAlert[]>([]);
  const [summary, setSummary] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dismissing, setDismissing] = useState<number | null>(null);

  const load = () => {
    if (!token) return;
    fetch(`http://localhost:8000/api/code-quality/secrets?repository_id=${repositoryId}&state=open&limit=20`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => { setAlerts(d.alerts || []); setSummary(d.summary || []); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [repositoryId, token]);

  const dismiss = async (id: number) => {
    setDismissing(id);
    await fetch(`http://localhost:8000/api/code-quality/secrets/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ state: "dismissed", resolution: "false_positive" }),
    });
    setAlerts((prev) => prev.filter((a) => a.id !== id));
    setDismissing(null);
  };

  const activeCount = alerts.filter((a) => a.validity === "active").length;
  const totalBypass = alerts.filter((a) => a.push_protection_bypassed).length;

  if (loading) return <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px", height: "360px" }} />;

  return (
    <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "15px", fontWeight: "bold", color: "#e2e8f0" }}>Secret Scan Alerts</h3>
          <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>{alerts.length} open · {activeCount} active · {totalBypass} bypass</p>
        </div>
        {alerts.length > 0 && <span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#ef4444", display: "inline-block" }} />}
      </div>

      {summary.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "16px" }}>
          {summary.slice(0, 5).map((s, i) => (
            <span key={i} style={{ fontSize: "11px", backgroundColor: "#450a0a", color: "#f87171", borderRadius: "20px", padding: "2px 10px", border: "1px solid #7f1d1d" }}>
              {s.secret_type.replace(/_/g, " ")} ({s.alert_count})
            </span>
          ))}
        </div>
      )}

      {alerts.length === 0 ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "48px 0", textAlign: "center" }}>
          <div style={{ fontSize: "32px", marginBottom: "8px" }}>🔒</div>
          <p style={{ color: "#e2e8f0", fontWeight: "bold", margin: "0 0 4px" }}>No open alerts</p>
          <p style={{ color: "#64748b", fontSize: "12px", margin: 0 }}>Secret scanning is active</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "384px", overflowY: "auto" }}>
          {alerts.map((alert) => (
            <div key={alert.id} style={{ display: "flex", alignItems: "flex-start", gap: "12px", padding: "12px", borderRadius: "10px", backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a" }}>
              <div style={{ fontSize: "16px", flexShrink: 0 }}>{alert.validity === "active" ? "🚨" : alert.validity === "unknown" ? "⚠️" : "🔕"}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "4px" }}>
                  <span style={{ fontSize: "11px", backgroundColor: "#2a2a4a", color: "#a78bfa", borderRadius: "4px", padding: "1px 6px" }}>{alert.tool}</span>
                  <span style={{ fontSize: "11px", fontWeight: "bold", color: VALIDITY_COLORS[alert.validity] || "#94a3b8" }}>{alert.validity}</span>
                  {alert.push_protection_bypassed && <span style={{ fontSize: "11px", backgroundColor: "#451a03", color: "#fbbf24", borderRadius: "4px", padding: "1px 6px" }}>bypass</span>}
                </div>
                <p style={{ margin: "0 0 2px", fontSize: "12px", fontWeight: "bold", color: "#e2e8f0" }}>{alert.secret_type_display || alert.secret_type.replace(/_/g, " ")}</p>
                {alert.filename && <p style={{ margin: "0 0 2px", fontSize: "11px", color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{alert.filename}{alert.line_number ? `:${alert.line_number}` : ""}</p>}
                <p style={{ margin: 0, fontSize: "11px", color: "#475569" }}>{formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}</p>
              </div>
              <button onClick={() => dismiss(alert.id)} disabled={dismissing === alert.id} style={{ fontSize: "12px", color: "#64748b", background: "none", border: "none", cursor: "pointer", flexShrink: 0 }}>
                {dismissing === alert.id ? "…" : "Dismiss"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
