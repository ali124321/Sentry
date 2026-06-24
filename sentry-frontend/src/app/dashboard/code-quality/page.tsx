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
      <div style={{ minHeight: "100vh", backgroundColor: "#0f0f1a", color: "#ffffff", fontFamily: "Arial, sans-serif", padding: "40px 32px" }}>
        <div style={{ backgroundColor: "#1a1a2e", border: "1px solid #2a2a4a", borderRadius: "16px", padding: "48px", textAlign: "center" }}>
          <p style={{ color: "#94a3b8", marginBottom: "16px", fontSize: "16px" }}>No repository selected.</p>
          <Link href="/dashboard/repos" style={{ color: "#a78bfa", fontWeight: 600, fontSize: "15px" }}>
            Select a repository
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f0f1a", color: "#ffffff", fontFamily: "Arial, sans-serif", padding: "40px 32px" }}>
      <div style={{ marginBottom: "32px" }}>
        <h2 style={{ fontSize: "32px", fontWeight: "bold", margin: "0 0 8px" }}>Code Quality</h2>
        <p style={{ color: "#64748b", margin: 0, fontSize: "16px" }}>
          Complexity, churn hotspots, lint density and secret scan alerts
        </p>
      </div>
      <div style={{ marginBottom: "24px" }}>
        <SummaryCards repositoryId={repoId} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "24px" }}>
        <ComplexityPanel repositoryId={repoId} />
        <ChurnPanel repositoryId={repoId} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        <LintPanel repositoryId={repoId} />
        <SecretAlertFeed repositoryId={repoId} />
      </div>
    </div>
  );
}
