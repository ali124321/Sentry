"use client";

import { useEffect, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { PanelSkeleton, Empty } from "./shared";
interface SecretAlert {
  id: number;
  secret_type: string;
  secret_type_display: string;
  tool: string;
  filename: string;
  line_number: number;
  validity: string;
  push_protection_bypassed: boolean;
  created_at: string;
  state: string;
}

const TOOL_COLORS: Record<string, string> = {
  gitleaks: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  semgrep: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  github: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
};

const VALIDITY_COLORS: Record<string, string> = {
  active: "text-red-600 dark:text-red-400",
  inactive: "text-gray-400",
  unknown: "text-yellow-600 dark:text-yellow-400",
};

export default function SecretAlertFeed({ repositoryId }: { repositoryId: number }) {
  const [alerts, setAlerts] = useState<SecretAlert[]>([]);
  const [summary, setSummary] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dismissing, setDismissing] = useState<number | null>(null);

  const load = () => {
    fetch(`/api/code-quality/secrets?repository_id=${repositoryId}&state=open&limit=20`)
      .then((r) => r.json())
      .then((d) => {
        setAlerts(d.alerts || []);
        setSummary(d.summary || []);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [repositoryId]);

  const dismiss = async (id: number) => {
    setDismissing(id);
    await fetch(`/api/code-quality/secrets/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state: "dismissed", resolution: "false_positive" }),
    });
    setAlerts((prev) => prev.filter((a) => a.id !== id));
    setDismissing(null);
  };

  const totalBypass = alerts.filter((a) => a.push_protection_bypassed).length;
  const activeCount = alerts.filter((a) => a.validity === "active").length;

  if (loading) return <PanelSkeleton title="Secret Scan Alerts" />;

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Secret Scan Alerts
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {alerts.length} open · {activeCount} active · {totalBypass} bypass
          </p>
        </div>
        {alerts.length > 0 && (
          <span className="flex h-2 w-2">
            <span className="animate-ping absolute h-2 w-2 rounded-full bg-red-400 opacity-75" />
            <span className="relative rounded-full h-2 w-2 bg-red-500" />
          </span>
        )}
      </div>

      {/* Summary pills */}
      {summary.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {summary.slice(0, 5).map((s, i) => (
            <span key={i} className="text-xs bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400 rounded-full px-2 py-0.5 border border-red-200 dark:border-red-800">
              {s.secret_type.replace(/_/g, " ")} ({s.alert_count})
            </span>
          ))}
        </div>
      )}

      {/* Alert list */}
      {alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="text-3xl mb-2">🔒</div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No open alerts</p>
          <p className="text-xs text-gray-400 mt-1">Secret scanning is active</p>
        </div>
      ) : (
        <div className="flex flex-col gap-3 max-h-96 overflow-y-auto pr-1">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800"
            >
              {/* Icon */}
              <div className="mt-0.5 text-base shrink-0">
                {alert.validity === "active" ? "🚨" : alert.validity === "unknown" ? "⚠️" : "🔕"}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${TOOL_COLORS[alert.tool] || TOOL_COLORS.github}`}>
                    {alert.tool}
                  </span>
                  <span className={`text-xs font-semibold ${VALIDITY_COLORS[alert.validity] || ""}`}>
                    {alert.validity}
                  </span>
                  {alert.push_protection_bypassed && (
                    <span className="text-xs bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 rounded px-1.5 py-0.5">
                      bypass
                    </span>
                  )}
                </div>
                <p className="text-xs font-medium text-gray-800 dark:text-gray-200 mt-1">
                  {alert.secret_type_display || alert.secret_type.replace(/_/g, " ")}
                </p>
                {alert.filename && (
                  <p className="text-xs text-gray-400 truncate mt-0.5">
                    {alert.filename}{alert.line_number ? `:${alert.line_number}` : ""}
                  </p>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                </p>
              </div>

              {/* Dismiss */}
              <button
                onClick={() => dismiss(alert.id)}
                disabled={dismissing === alert.id}
                className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 shrink-0 transition-colors disabled:opacity-40"
              >
                {dismissing === alert.id ? "…" : "Dismiss"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}