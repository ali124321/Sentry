"use client";

import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { PanelSkeleton, Empty } from "./shared";
interface LintSummary {
  tool: string;
  severity: string;
  category: string;
  finding_count: number;
  affected_files: number;
}

interface TopFile {
  filename: string;
  total_findings: number;
  errors: number;
  warnings: number;
}

const SEVERITY_COLORS: Record<string, string> = {
  error: "#ef4444",
  warning: "#f97316",
  info: "#3b82f6",
  hint: "#8b5cf6",
};

export default function LintPanel({ repositoryId }: { repositoryId: number }) {
  const [summary, setSummary] = useState<LintSummary[]>([]);
  const [topFiles, setTopFiles] = useState<TopFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/code-quality/lint?repository_id=${repositoryId}&limit=10`)
      .then((r) => r.json())
      .then((d) => {
        setSummary(d.summary || []);
        setTopFiles(d.top_files || []);
      })
      .finally(() => setLoading(false));
  }, [repositoryId]);

  const pieData = Object.entries(
    summary.reduce((acc, s) => {
      acc[s.severity] = (acc[s.severity] || 0) + s.finding_count;
      return acc;
    }, {} as Record<string, number>)
  ).map(([name, value]) => ({ name, value }));

  const totalFindings = pieData.reduce((s, d) => s + d.value, 0);

  if (loading) return <PanelSkeleton title="Lint Density" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Lint Density</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {totalFindings.toLocaleString()} open findings
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Pie chart */}
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value">
              {pieData.map((entry, i) => (
                <Cell key={i} fill={SEVERITY_COLORS[entry.name] || "#6b7280"} />
              ))}
            </Pie>
            <Tooltip formatter={(value: any) => (typeof value === "number" ? value.toLocaleString() : value != null ? String(value) : "")} />
            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          </PieChart>
        </ResponsiveContainer>

        {/* Top files */}
        <div className="flex flex-col gap-1.5 overflow-hidden">
          <p className="text-xs font-medium text-gray-500 mb-1">Top offending files</p>
          {topFiles.slice(0, 6).map((f, i) => (
            <div key={i} className="flex items-center justify-between gap-2">
              <span className="text-xs text-gray-700 dark:text-gray-300 truncate flex-1">
                {f.filename.split("/").pop()}
              </span>
              <div className="flex items-center gap-1 shrink-0">
                {f.errors > 0 && (
                  <span className="text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded px-1.5 py-0.5">
                    {f.errors}E
                  </span>
                )}
                {f.warnings > 0 && (
                  <span className="text-xs bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 rounded px-1.5 py-0.5">
                    {f.warnings}W
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
