"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthContext";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, ZAxis } from "recharts";

interface Hotspot {
  filename: string;
  complexity_score: number;
  churn: number;
  commit_count: number;
  distinct_authors: number;
  churn_complexity_score: number;
}

export default function ChurnPanel({ repositoryId }: { repositoryId: number }) {
  const { token } = useAuth();
  const [data, setData] = useState<Hotspot[]>([]);
  const [window, setWindow] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetch(`http://localhost:8000/api/code-quality/churn?repository_id=${repositoryId}&window=${window}&limit=40`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => setData(d.hotspots || []))
      .finally(() => setLoading(false));
  }, [repositoryId, window, token]);

  const chartData = data.map((h) => ({
    x: Number(h.complexity_score) || 0,
    y: h.churn,
    z: h.commit_count,
    name: h.filename.split("/").pop(),
    fullPath: h.filename,
    authors: h.distinct_authors,
  }));

  if (loading) return (
    <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px", height: "360px" }} />
  );

  return (
    <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "15px", fontWeight: "bold", color: "#e2e8f0" }}>Churn Hotspots</h3>
          <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>Complexity × churn — bubble size = commits</p>
        </div>
        <div style={{ display: "flex", borderRadius: "8px", overflow: "hidden", border: "1px solid #2a2a4a" }}>
          {[30, 90].map((w) => (
            <button
              key={w}
              onClick={() => setWindow(w)}
              style={{
                padding: "6px 14px",
                fontSize: "12px",
                border: "none",
                cursor: "pointer",
                backgroundColor: window === w ? "#7c3aed" : "#0f0f1a",
                color: window === w ? "#fff" : "#94a3b8",
                fontWeight: window === w ? "bold" : "normal",
              }}
            >
              {w}d
            </button>
          ))}
        </div>
      </div>
      {chartData.length === 0 ? (
        <p style={{ color: "#64748b", textAlign: "center", padding: "48px 0" }}>No churn data yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <XAxis dataKey="x" name="Complexity" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} label={{ value: "Complexity", position: "insideBottom", offset: -4, fontSize: 11, fill: "#64748b" }} />
            <YAxis dataKey="y" name="Churn" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} label={{ value: "Churn", angle: -90, position: "insideLeft", fontSize: 11, fill: "#64748b" }} />
            <ZAxis dataKey="z" range={[40, 400]} />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div style={{ backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "8px", padding: "10px 14px", fontSize: "12px", color: "#e2e8f0" }}>
                    <p style={{ margin: "0 0 4px", fontWeight: "bold" }}>{d.fullPath}</p>
                    <p style={{ margin: 0 }}>Complexity: {d.x}</p>
                    <p style={{ margin: 0 }}>Churn: {d.y} lines</p>
                    <p style={{ margin: 0 }}>Commits: {d.z}</p>
                    <p style={{ margin: 0 }}>Authors: {d.authors}</p>
                  </div>
                );
              }}
            />
            <Scatter data={chartData} fill="#a78bfa" fillOpacity={0.7} />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
