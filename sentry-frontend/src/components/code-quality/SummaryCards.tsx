"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthContext";

interface Summary {
  overall_risk_score: number;
  complexity: { total_files: number; avg_complexity: number; high_complexity_files: number };
  churn: { active_files_30d: number; critical_hotspots: number };
  lint: { total_open_findings: number; errors: number };
  secrets: { open_alerts: number; active_secrets: number; bypass_count: number };
}

export default function SummaryCards({ repositoryId }: { repositoryId: number }) {
  const { token } = useAuth();
  const [data, setData] = useState<Summary | null>(null);

  useEffect(() => {
    if (!token) return;
    fetch(`http://localhost:8000/api/code-quality/summary?repository_id=${repositoryId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => { if (d.complexity) setData(d); });
  }, [repositoryId, token]);

  if (!data) return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "16px" }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} style={{ height: "96px", borderRadius: "16px", backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a" }} />
      ))}
    </div>
  );

  const riskColor = data.overall_risk_score >= 60 ? "#f87171" : data.overall_risk_score >= 30 ? "#fb923c" : "#34d399";

  const cards = [
    { label: "Risk Score", value: `${data.overall_risk_score}/100`, sub: "Overall", color: riskColor, icon: "🎯" },
    { label: "Complex Files", value: data.complexity.high_complexity_files, sub: `avg ${data.complexity.avg_complexity} score`, color: data.complexity.high_complexity_files > 10 ? "#f87171" : "#e2e8f0", icon: "🧩" },
    { label: "Hotspots", value: data.churn.critical_hotspots, sub: `${data.churn.active_files_30d} active files`, color: data.churn.critical_hotspots > 5 ? "#fb923c" : "#e2e8f0", icon: "🔥" },
    { label: "Lint Errors", value: data.lint.errors?.toLocaleString(), sub: `${data.lint.total_open_findings?.toLocaleString()} total findings`, color: data.lint.errors > 50 ? "#f87171" : "#e2e8f0", icon: "🔍" },
    { label: "Secret Alerts", value: data.secrets.open_alerts, sub: `${data.secrets.active_secrets} active · ${data.secrets.bypass_count} bypassed`, color: data.secrets.open_alerts > 0 ? "#f87171" : "#34d399", icon: "🔑" },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "16px" }}>
      {cards.map((card, i) => (
        <div key={i} style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
            <span style={{ fontSize: "16px" }}>{card.icon}</span>
            <span style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "bold" }}>{card.label}</span>
          </div>
          <p style={{ fontSize: "28px", fontWeight: "bold", color: card.color, margin: "0 0 4px" }}>{card.value}</p>
          <p style={{ color: "#64748b", fontSize: "11px", margin: 0 }}>{card.sub}</p>
        </div>
      ))}
    </div>
  );
}
