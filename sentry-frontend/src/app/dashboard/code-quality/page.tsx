"use client";

import { useAuth } from "@/lib/auth/AuthContext";
import SummaryCards from "@/components/code-quality/SummaryCards";
import ComplexityPanel from "@/components/code-quality/ComplexityPanel";
import ChurnPanel from "@/components/code-quality/ChurnPanel";
import LintPanel from "@/components/code-quality/LintPanel";
import SecretAlertFeed from "@/components/code-quality/SecretAlertFeed";
import Link from "next/link";

export default function CodeQualityPage() {
  const { selectedRepoId } = useAuth();
  const repoId = selectedRepoId || 1;

  if (!selectedRepoId) {
    return (
      <div className="p-6 max-w-screen-xl mx-auto">
        <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "12px", padding: "32px", textAlign: "center" }}>
          <p style={{ color: "#94a3b8", marginBottom: "12px" }}>No repository selected.</p>
          <Link href="/dashboard/repos" style={{ color: "#f97316", fontWeight: 600 }}>
            Select a repository
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Code Quality</h1>
        <p className="text-sm text-gray-500 mt-1">
          Complexity, churn hotspots, lint density and secret scan alerts
        </p>
      </div>

      {/* KPI summary row */}
      <SummaryCards repositoryId={repoId} />

      {/* Main panels — 2 column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ComplexityPanel repositoryId={repoId} />
        <ChurnPanel repositoryId={repoId} />
      </div>

      {/* Lint + Secrets — 2 column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LintPanel repositoryId={repoId} />
        <SecretAlertFeed repositoryId={repoId} />
      </div>
    </div>
  );
}