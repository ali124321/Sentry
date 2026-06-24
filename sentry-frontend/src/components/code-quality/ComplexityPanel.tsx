"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthContext";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface FileMetric {
  filename: string;
  language: string;
  complexity_score: number;
  loc: number;
  functions_count: number;
}

export default function ComplexityPanel({ repositoryId }: { repositoryId: number }) {
  const { token } = useAuth();
  const [data, setData] = useState<FileMetric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    fetch(`http://localhost:8000/api/code-quality/complexity?repository_id=${repositoryId}&limit=15`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => setData(d.files || []))
      .finally(() => setLoading(false));
  }, [repositoryId, token]);

  const getColor = (score: number) => {
    if (score >= 20) return "#ef4444";
    if (score >= 10) return "#f97316";
    return "#22c55e";
  };

  const chartData = data.map((f) => ({
    name: f.filename.split("/").pop(),
    fullPath: f.filename,
    score: Number(f.complexity_score),
    loc: f.loc,
  }));

  if (loading) return (
    <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px", height: "360px" }} />
  );

  return (
    <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "15px", fontWeight: "bold", color: "#e2e8f0" }}>Cyclomatic Complexity</h3>
          <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>Top 15 most complex files</p>
        </div>
        <div style={{ display: "flex", gap: "12px", fontSize: "11px", color: "#64748b" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#22c55e", display: "inline-block" }} />Low</span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#f97316", display: "inline-block" }} />Medium</span>
          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#ef4444", display: "inline-block" }} />High</span>
        </div>
      </div>
      {chartData.length === 0 ? (
        <p style={{ color: "#64748b", textAlign: "center", padding: "48px 0" }}>No complexity data yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
            <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: "#94a3b8" }} tickFormatter={(v) => (v.length > 18 ? v.slice(0, 18) + "…" : v)} axisLine={false} tickLine={false} />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div style={{ backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "8px", padding: "10px 14px", fontSize: "12px", color: "#e2e8f0" }}>
                    <p style={{ margin: "0 0 4px", fontWeight: "bold" }}>{d.fullPath}</p>
                    <p style={{ margin: 0 }}>Complexity: <strong>{d.score}</strong></p>
                    <p style={{ margin: 0 }}>LOC: {d.loc}</p>
                  </div>
                );
              }}
            />
            <Bar dataKey="score" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={getColor(entry.score)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
