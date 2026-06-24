"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthContext";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface LintSummary { tool: string; severity: string; category: string; finding_count: number; affected_files: number; }
interface TopFile { filename: string; total_findings: number; errors: number; warnings: number; }

const SEVERITY_COLORS: Record<string, string> = { error: "#ef4444", warning: "#f97316", info: "#3b82f6", hint: "#8b5cf6" };

export default function LintPanel({ repositoryId }: { repositoryId: number }) {
  const { token } = useAuth();
  const [summary, setSummary] = useState<LintSummary[]>([]);
  const [topFiles, setTopFiles] = useState<TopFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    fetch(`http://localhost:8000/api/code-quality/lint?repository_id=${repositoryId}&limit=10`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => { setSummary(d.summary || []); setTopFiles(d.top_files || []); })
      .finally(() => setLoading(false));
  }, [repositoryId, token]);

  const pieData = Object.entries(
    summary.reduce((acc, s) => { acc[s.severity] = (acc[s.severity] || 0) + s.finding_count; return acc; }, {} as Record<string, number>)
  ).map(([name, value]) => ({ name, value }));

  const totalFindings = pieData.reduce((s, d) => s + d.value, 0);

  if (loading) return <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px", height: "360px" }} />;

  return (
    <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "24px" }}>
      <div style={{ marginBottom: "16px" }}>
        <h3 style={{ margin: 0, fontSize: "15px", fontWeight: "bold", color: "#e2e8f0" }}>Lint Density</h3>
        <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#64748b" }}>{totalFindings.toLocaleString()} open findings</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value">
              {pieData.map((entry, i) => <Cell key={i} fill={SEVERITY_COLORS[entry.name] || "#6b7280"} />)}
            </Pie>
            <Tooltip formatter={(v: any) => (typeof v === "number" ? v.toLocaleString() : String(v ?? ""))} contentStyle={{ backgroundColor: "#0f0f1a", border: "1px solid #2a2a4a", borderRadius: "8px", color: "#e2e8f0" }} />
            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <p style={{ margin: "0 0 4px", fontSize: "12px", color: "#64748b", fontWeight: "bold" }}>Top offending files</p>
          {topFiles.slice(0, 6).map((f, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "12px", color: "#94a3b8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{f.filename.split("/").pop()}</span>
              <div style={{ display: "flex", gap: "4px", flexShrink: 0 }}>
                {f.errors > 0 && <span style={{ fontSize: "11px", backgroundColor: "#450a0a", color: "#f87171", borderRadius: "4px", padding: "1px 6px" }}>{f.errors}E</span>}
                {f.warnings > 0 && <span style={{ fontSize: "11px", backgroundColor: "#431407", color: "#fb923c", borderRadius: "4px", padding: "1px 6px" }}>{f.warnings}W</span>}
              </div>
            </div>
          ))}
          {topFiles.length === 0 && <p style={{ color: "#64748b", fontSize: "12px" }}>No findings</p>}
        </div>
      </div>
    </div>
  );
}
