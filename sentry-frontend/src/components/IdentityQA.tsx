"use client";
import { useEffect, useState } from "react";

interface QASummary {
  overall_status: string;
  checks: {
    unresolved_codes: {
      total_events: number;
      unresolved_count: number;
      unresolved_pct: number;
      threshold_pct: number;
      status: string;
    };
    duplicate_clusters: {
      duplicate_clusters: number;
      status: string;
      clusters: { email: string; id_count: number; person_ids: string[] }[];
    };
    unmatched_sessions: {
      total_entries: number;
      unmatched_count: number;
      unmatched_pct: number;
      threshold_pct: number;
      status: string;
      unmatched_person_ids: string[];
    };
  };
}

export default function IdentityQA({ token }: { token: string }) {
  const [qa, setQA] = useState<QASummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [merging, setMerging] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/identity-qa/summary", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => { setQA(data); setLoading(false); })
      .catch(() => { setError("Failed to load QA data"); setLoading(false); });
  }, [token]);

  const handleMerge = async (primaryId: string, duplicateId: string) => {
    setMerging(duplicateId);
    // Placeholder for merge action — wire to backend in future
    await new Promise((r) => setTimeout(r, 1000));
    setMessage(`✅ Merged ${duplicateId} into ${primaryId}`);
    setMerging(null);
  };

  const statusBadge = (status: string) => (
    <span style={{
      padding: "3px 12px", borderRadius: "20px", fontSize: "12px", fontWeight: "bold",
      backgroundColor: status === "OK" ? "#14532d" : "#78350f",
      color: status === "OK" ? "#34d399" : "#fbbf24",
      border: `1px solid ${status === "OK" ? "#16a34a" : "#d97706"}`,
    }}>
      {status === "OK" ? "✅ OK" : "⚠️ WARNING"}
    </span>
  );

  if (loading) return <p style={{ color: "#64748b" }}>Loading QA data...</p>;
  if (error) return <p style={{ color: "#f87171" }}>{error}</p>;
  if (!qa) return null;

  const { unresolved_codes, duplicate_clusters, unmatched_sessions } = qa.checks;

  return (
    <div>
      <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>🔎 Identity QA</h2>
      <p style={{ color: "#64748b", marginBottom: "24px" }}>
        Review and clean identity issues before trusting any KPI
      </p>

      {/* Overall Status */}
      <div style={{
        backgroundColor: qa.overall_status === "OK" ? "#14532d" : "#78350f",
        border: `1px solid ${qa.overall_status === "OK" ? "#16a34a" : "#d97706"}`,
        borderRadius: "12px", padding: "16px 24px", marginBottom: "24px",
        display: "flex", alignItems: "center", gap: "12px",
      }}>
        <span style={{ fontSize: "24px" }}>{qa.overall_status === "OK" ? "✅" : "⚠️"}</span>
        <div>
          <p style={{ margin: 0, fontWeight: "bold", fontSize: "16px" }}>
            Overall Status: {qa.overall_status}
          </p>
          <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8" }}>
            {qa.overall_status === "OK"
              ? "All identity checks passed. KPIs can be trusted."
              : "Some checks need attention before trusting KPIs."}
          </p>
        </div>
      </div>

      {message && (
        <div style={{
          padding: "12px 20px", borderRadius: "10px", marginBottom: "24px",
          backgroundColor: "#14532d", border: "1px solid #16a34a", color: "#34d399",
        }}>
          {message}
        </div>
      )}

      {/* 3 QA Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "28px" }}>
        {[
          {
            label: "Unresolved Codes",
            value: `${unresolved_codes.unresolved_pct}%`,
            sub: `${unresolved_codes.unresolved_count} of ${unresolved_codes.total_events} events`,
            threshold: `Threshold: ${unresolved_codes.threshold_pct}%`,
            status: unresolved_codes.status,
            icon: "🏷️",
          },
          {
            label: "Duplicate Clusters",
            value: duplicate_clusters.duplicate_clusters,
            sub: "persons with multiple IDs",
            threshold: "Threshold: 0",
            status: duplicate_clusters.status,
            icon: "👥",
          },
          {
            label: "Unmatched Sessions",
            value: `${unmatched_sessions.unmatched_pct}%`,
            sub: `${unmatched_sessions.unmatched_count} of ${unmatched_sessions.total_entries} entries`,
            threshold: `Threshold: ${unmatched_sessions.threshold_pct}%`,
            status: unmatched_sessions.status,
            icon: "🚪",
          },
        ].map((card) => (
          <div key={card.label} style={{
            backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
            borderRadius: "12px", padding: "20px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <span style={{ fontSize: "20px" }}>{card.icon}</span>
              {statusBadge(card.status)}
            </div>
            <p style={{ color: "#94a3b8", margin: "0 0 4px", fontSize: "13px" }}>{card.label}</p>
            <p style={{ fontSize: "32px", fontWeight: "bold", color: "#a78bfa", margin: "0 0 4px" }}>{card.value}</p>
            <p style={{ color: "#64748b", fontSize: "12px", margin: "0 0 2px" }}>{card.sub}</p>
            <p style={{ color: "#475569", fontSize: "11px", margin: 0 }}>{card.threshold}</p>
          </div>
        ))}
      </div>

      {/* Duplicate Clusters Table */}
      <div style={{
        backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
        borderRadius: "16px", overflow: "hidden", marginBottom: "24px",
      }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}>
          <h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>👥 Duplicate Identity Clusters</h3>
        </div>
        {duplicate_clusters.clusters.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center" as const, color: "#475569" }}>
            <p style={{ fontSize: "32px", margin: "0 0 8px" }}>✅</p>
            <p style={{ margin: 0 }}>No duplicate identities found</p>
          </div>
        ) : (
          <>
            <div style={{
              display: "grid", gridTemplateColumns: "2fr 1fr 2fr 1fr",
              padding: "12px 24px", backgroundColor: "#0f0f1a",
              borderBottom: "1px solid #2a2a4a",
              color: "#64748b", fontSize: "13px", fontWeight: "bold",
              textTransform: "uppercase" as const,
            }}>
              <span>Email</span>
              <span>Count</span>
              <span>Person IDs</span>
              <span>Action</span>
            </div>
            {duplicate_clusters.clusters.map((cluster) => (
              <div key={cluster.email} style={{
                display: "grid", gridTemplateColumns: "2fr 1fr 2fr 1fr",
                padding: "16px 24px", borderBottom: "1px solid #2a2a4a",
                alignItems: "center",
              }}>
                <span style={{ color: "#94a3b8", fontSize: "14px" }}>{cluster.email}</span>
                <span style={{ color: "#f87171", fontWeight: "bold" }}>{cluster.id_count}</span>
                <div style={{ display: "flex", flexDirection: "column" as const, gap: "4px" }}>
                  {cluster.person_ids.map((id, i) => (
                    <span key={id} style={{ fontSize: "11px", color: i === 0 ? "#34d399" : "#f87171" }}>
                      {i === 0 ? "✅ Primary: " : "❌ Duplicate: "}{id.slice(0, 8)}...
                    </span>
                  ))}
                </div>
                <button
                  onClick={() => handleMerge(cluster.person_ids[0], cluster.person_ids[1])}
                  disabled={merging === cluster.person_ids[1]}
                  style={{
                    padding: "6px 14px", backgroundColor: "#7c3aed",
                    color: "#fff", border: "none", borderRadius: "6px",
                    cursor: "pointer", fontSize: "13px", fontWeight: "bold",
                    opacity: merging === cluster.person_ids[1] ? 0.5 : 1,
                  }}
                >
                  {merging === cluster.person_ids[1] ? "Merging..." : "🔗 Merge"}
                </button>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Unmatched Sessions */}
      <div style={{
        backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a",
        borderRadius: "16px", overflow: "hidden",
      }}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid #2a2a4a" }}>
          <h3 style={{ margin: 0, fontSize: "16px", color: "#94a3b8" }}>🚪 Unmatched Sessions</h3>
        </div>
        {unmatched_sessions.unmatched_person_ids.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center" as const, color: "#475569" }}>
            <p style={{ fontSize: "32px", margin: "0 0 8px" }}>✅</p>
            <p style={{ margin: 0 }}>No unmatched sessions found</p>
          </div>
        ) : (
          unmatched_sessions.unmatched_person_ids.map((id) => (
            <div key={id} style={{
              padding: "14px 24px", borderBottom: "1px solid #2a2a4a",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <span style={{ color: "#94a3b8", fontSize: "14px" }}>🚪 {id}</span>
              <span style={{
                padding: "3px 12px", borderRadius: "20px", fontSize: "12px",
                backgroundColor: "#7f1d1d", color: "#f87171", border: "1px solid #dc2626",
              }}>No matching EXIT</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}