import SummaryCards from "@/components/code-quality/SummaryCards";
import ComplexityPanel from "@/components/code-quality/ComplexityPanel";
import ChurnPanel from "@/components/code-quality/ChurnPanel";
import LintPanel from "@/components/code-quality/LintPanel";
import SecretAlertFeed from "@/components/code-quality/SecretAlertFeed";

// Replace with dynamic repo selection as needed
const DEFAULT_REPO_ID = 1;

export default function CodeQualityPage() {
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
      <SummaryCards repositoryId={DEFAULT_REPO_ID} />

      {/* Main panels — 2 column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ComplexityPanel repositoryId={DEFAULT_REPO_ID} />
        <ChurnPanel repositoryId={DEFAULT_REPO_ID} />
      </div>

      {/* Lint + Secrets — 2 column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LintPanel repositoryId={DEFAULT_REPO_ID} />
        <SecretAlertFeed repositoryId={DEFAULT_REPO_ID} />
      </div>
    </div>
  );
}