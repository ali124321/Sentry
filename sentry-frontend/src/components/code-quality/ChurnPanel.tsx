"use client";

import { useEffect, useState } from "react";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, ZAxis } from "recharts";
import { PanelSkeleton, Empty } from "./shared";
interface Hotspot {
  filename: string;
  complexity_score: number;
  churn: number;
  commit_count: number;
  distinct_authors: number;
  churn_complexity_score: number;
}

export default function ChurnPanel({ repositoryId }: { repositoryId: number }) {
  const [data, setData] = useState<Hotspot[]>([]);
  const [window, setWindow] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/code-quality/churn?repository_id=${repositoryId}&window=${window}&limit=40`)
      .then((r) => r.json())
      .then((d) => setData(d.hotspots || []))
      .finally(() => setLoading(false));
  }, [repositoryId, window]);

  const chartData = data.map((h) => ({
    x: Number(h.complexity_score) || 0,
    y: h.churn,
    z: h.commit_count,
    name: h.filename.split("/").pop(),
    fullPath: h.filename,
    authors: h.distinct_authors,
  }));

  if (loading) return <PanelSkeleton title="Churn Hotspots" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Churn Hotspots</h3>
          <p className="text-xs text-gray-500 mt-0.5">Complexity × churn — bubble size = commits</p>
        </div>
        <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 text-xs">
          {[30, 90].map((w) => (
            <button
              key={w}
              onClick={() => setWindow(w)}
              className={`px-3 py-1 transition-colors ${
                window === w
                  ? "bg-blue-600 text-white"
                  : "bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-50"
              }`}
            >
              {w}d
            </button>
          ))}
        </div>
      </div>

      {chartData.length === 0 ? (
        <Empty message="No churn data yet" />
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <XAxis dataKey="x" name="Complexity" tick={{ fontSize: 11 }} label={{ value: "Complexity", position: "insideBottom", offset: -4, fontSize: 11 }} />
            <YAxis dataKey="y" name="Churn" tick={{ fontSize: 11 }} label={{ value: "Churn", angle: -90, position: "insideLeft", fontSize: 11 }} />
            <ZAxis dataKey="z" range={[40, 400]} />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl max-w-xs">
                    <p className="font-medium truncate mb-1">{d.fullPath}</p>
                    <p>Complexity: {d.x}</p>
                    <p>Churn: {d.y} lines</p>
                    <p>Commits: {d.z}</p>
                    <p>Authors: {d.authors}</p>
                  </div>
                );
              }}
            />
            <Scatter data={chartData} fill="#3b82f6" fillOpacity={0.7} />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
