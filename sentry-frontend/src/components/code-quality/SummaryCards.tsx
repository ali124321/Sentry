"use client";

import { useEffect, useState } from "react";

interface Summary {
  overall_risk_score: number;
  complexity: { total_files: number; avg_complexity: number; high_complexity_files: number };
  churn: { active_files_30d: number; critical_hotspots: number };
  lint: { total_open_findings: number; errors: number };
  secrets: { open_alerts: number; active_secrets: number; bypass_count: number };
}

export default function SummaryCards({ repositoryId }: { repositoryId: number }) {
  const [data, setData] = useState<Summary | null>(null);

  useEffect(() => {
    fetch(`/api/code-quality/summary?repository_id=${repositoryId}`)
      .then((r) => r.json())
      .then(setData);
  }, [repositoryId]);

  if (!data) return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-24 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
      ))}
    </div>
  );

  const riskColor =
    data.overall_risk_score >= 60 ? "text-red-600 dark:text-red-400"
    : data.overall_risk_score >= 30 ? "text-orange-500 dark:text-orange-400"
    : "text-green-600 dark:text-green-400";

  const cards = [
    {
      label: "Risk Score",
      value: `${data.overall_risk_score}/100`,
      sub: "Overall",
      valueClass: riskColor,
      icon: "🎯",
    },
    {
      label: "Complex Files",
      value: data.complexity.high_complexity_files,
      sub: `avg ${data.complexity.avg_complexity} score`,
      valueClass: data.complexity.high_complexity_files > 10 ? "text-red-600 dark:text-red-400" : "text-gray-900 dark:text-gray-100",
      icon: "🧩",
    },
    {
      label: "Hotspots",
      value: data.churn.critical_hotspots,
      sub: `${data.churn.active_files_30d} active files`,
      valueClass: data.churn.critical_hotspots > 5 ? "text-orange-500" : "text-gray-900 dark:text-gray-100",
      icon: "🔥",
    },
    {
      label: "Lint Errors",
      value: data.lint.errors?.toLocaleString(),
      sub: `${data.lint.total_open_findings?.toLocaleString()} total findings`,
      valueClass: data.lint.errors > 50 ? "text-red-600 dark:text-red-400" : "text-gray-900 dark:text-gray-100",
      icon: "🔍",
    },
    {
      label: "Secret Alerts",
      value: data.secrets.open_alerts,
      sub: `${data.secrets.active_secrets} active · ${data.secrets.bypass_count} bypassed`,
      valueClass: data.secrets.open_alerts > 0 ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400",
      icon: "🔑",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
      {cards.map((card, i) => (
        <div
          key={i}
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">{card.icon}</span>
            <span className="text-xs text-gray-500 font-medium">{card.label}</span>
          </div>
          <p className={`text-2xl font-bold ${card.valueClass}`}>{card.value}</p>
          <p className="text-xs text-gray-400 mt-1">{card.sub}</p>
        </div>
      ))}
    </div>
  );
}