"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { PanelSkeleton, Empty } from "./shared";
interface FileMetric {
  filename: string;
  language: string;
  complexity_score: number;
  loc: number;
  functions_count: number;
}

export default function ComplexityPanel({ repositoryId }: { repositoryId: number }) {
  const [data, setData] = useState<FileMetric[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/code-quality/complexity?repository_id=${repositoryId}&limit=15`)
      .then((r) => r.json())
      .then((d) => setData(d.files || []))
      .finally(() => setLoading(false));
  }, [repositoryId]);

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

  if (loading) return <PanelSkeleton title="Cyclomatic Complexity" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Cyclomatic Complexity
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">Top 15 most complex files</p>
        </div>
        <Legend />
      </div>

      {chartData.length === 0 ? (
        <Empty message="No complexity data yet" />
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="name"
              width={120}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => (v.length > 18 ? v.slice(0, 18) + "…" : v)}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl max-w-xs">
                    <p className="font-medium truncate mb-1">{d.fullPath}</p>
                    <p>Complexity: <span className="font-bold">{d.score}</span></p>
                    <p>LOC: {d.loc}</p>
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

function Legend() {
  return (
    <div className="flex items-center gap-3 text-xs text-gray-500">
      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block" />Low</span>
      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500 inline-block" />Medium</span>
      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" />High</span>
    </div>
  );
}