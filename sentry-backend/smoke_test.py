#!/usr/bin/env python3
"""
Smoke test: hits every read-only GET endpoint with a valid token
and reports status codes. Skips endpoints needing path params we
don't have real values for, and skips all mutating verbs.
"""
import requests
import sys

BASE = "http://localhost:8000"

LOGIN_EMAIL = "ahmed@example.com"
LOGIN_PASSWORD = "password123"

GET_ENDPOINTS = [
    "/api/v1/me",
    "/api/v1/dashboard",
    "/api/v1/users/",
    "/api/v1/users/audit-logs",
    "/api/v1/users/me",
    "/api/v1/identity-qa/unresolved-codes",
    "/api/v1/identity-qa/duplicate-clusters",
    "/api/v1/identity-qa/unmatched-sessions",
    "/api/v1/identity-qa/summary",
    "/api/v1/sync/status",
    "/api/v1/sync/schedule",
    "/api/v1/sync/runs",
    "/api/v1/sync/health",
    "/api/v1/attendance/days-present",
    "/api/v1/attendance/first-entry",
    "/api/v1/attendance/sessions",
    "/api/v1/kpi/attendance/days-present",
    "/api/v1/kpi/attendance/avg-arrival",
    "/api/v1/kpi/attendance/arrival-consistency",
    "/api/v1/kpi/attendance/session-hours",
    "/api/v1/kpi/attendance/trend",
    "/api/v1/kpi/attendance/cohort-summary",
    "/api/v1/occupancy/running",
    "/api/v1/occupancy/daily-peak",
    "/api/v1/occupancy/mobile-vs-card",
    "/api/v1/occupancy-kpi/peak",
    "/api/v1/occupancy-kpi/trend",
    "/api/v1/occupancy-kpi/forecast",
    "/api/v1/occupancy-kpi/mobile-adoption",
    "/api/v1/anomalies/denied-access",
    "/api/v1/anomalies/entry-exit-imbalance",
    "/api/v1/anomalies/queue",
    "/api/v1/security/metrics/denied-access",
    "/api/v1/security/metrics/imbalance",
    "/api/v1/security/review-queue",
    "/api/v1/security/review-queue/summary",
    "/api/code-quality/complexity?repository_id=4",
    "/api/code-quality/churn?repository_id=4",
    "/api/code-quality/lint?repository_id=4",
    "/api/code-quality/secrets?repository_id=4",
    "/api/code-quality/summary?repository_id=4",
    "/api/v1/dora/deployment-frequency",
    "/api/v1/dora/lead-time",
    "/api/v1/dora/change-failure-rate",
    "/api/v1/dora/time-to-restore",
    "/api/v1/dora/review-latency",
    "/api/v1/dora-kpi/deployment-frequency",
    "/api/v1/dora-kpi/lead-time",
    "/api/v1/dora-kpi/change-failure-rate",
    "/api/v1/dora-kpi/time-to-restore",
    "/api/v1/dora-kpi/review-latency",
    "/api/v1/dora-kpi/szz/traces",
    "/api/v1/dora-kpi/szz/top-bug-introducers",
    "/api/v1/defect-risk/scores",
    "/api/v1/defect-risk/watchlist",
    "/api/v1/suppression/demo",
    "/api/v1/ml/runs",
    "/api/v1/governance/caveats",
    "/api/v1/cohorts/summary",
    "/api/v1/cohorts/centroids",
    "/api/v1/cohorts/assignments",
    "/api/v1/cohorts/overview",
    "/api/v1/repos/github",
    "/api/v1/repos/",
    "/health",
    "/",
]


def main():
    login = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
        timeout=10,
    )
    if login.status_code != 200:
        print(f"LOGIN FAILED: {login.status_code} {login.text}")
        sys.exit(1)

    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    results = {"ok": [], "error": []}

    for path in GET_ENDPOINTS:
        url = f"{BASE}{path}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            status = r.status_code
            if status < 400:
                results["ok"].append((path, status))
            else:
                body = r.text[:200].replace("\n", " ")
                results["error"].append((path, status, body))
        except Exception as e:
            results["error"].append((path, "EXCEPTION", str(e)[:200]))

    print(f"\n{'='*70}")
    print(f"OK: {len(results['ok'])} / {len(GET_ENDPOINTS)}")
    print(f"{'='*70}")

    if results["error"]:
        print(f"\nFAILED ENDPOINTS ({len(results['error'])}):\n")
        for item in results["error"]:
            if len(item) == 3:
                path, status, body = item
                print(f"  [{status}] {path}")
                print(f"      {body}")
            else:
                path, status = item
                print(f"  [{status}] {path}")
    else:
        print("\nAll tested endpoints returned successfully!")


if __name__ == "__main__":
    main()
