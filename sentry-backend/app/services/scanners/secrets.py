"""
SENTRY-32: Secret & vulnerability scanner — gitleaks + semgrep.
Writes to secret_scan_alert and fires immediate alerts.
"""

import json
import logging
import subprocess
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.alerts import send_alert

logger = logging.getLogger(__name__)


def _run(cmd: list[str], cwd: str) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    return result.stdout


# --------------------------------------------------------------------------- #
# Gitleaks                                                                     #
# --------------------------------------------------------------------------- #

def run_gitleaks(repo_path: str) -> list[dict]:
    raw = _run(
        ["gitleaks", "detect", "--source", repo_path,
         "--report-format", "json", "--report-path", "/dev/stdout",
         "--no-banner", "--exit-code", "0"],
        cwd=repo_path,
    )
    if not raw.strip():
        return []

    try:
        results = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("[gitleaks] failed to parse JSON output")
        return []

    findings = []
    for item in results:
        findings.append({
            "secret_type": item.get("RuleID", "unknown"),
            "secret_type_display": item.get("Description"),
            "tool": "gitleaks",
            "filename": item.get("File"),
            "commit_sha": item.get("Commit"),
            "line_number": item.get("StartLine"),
            "validity": "unknown",
            "state": "open",
        })
    return findings


# --------------------------------------------------------------------------- #
# Semgrep                                                                      #
# --------------------------------------------------------------------------- #

def run_semgrep(repo_path: str) -> list[dict]:
    raw = _run(
        ["semgrep", "scan", "--config", "p/secrets", "--config", "p/security-audit",
         "--json", "--quiet"],
        cwd=repo_path,
    )
    if not raw.strip():
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("[semgrep] failed to parse JSON output")
        return []

    findings = []
    for item in data.get("results", []):
        meta = item.get("extra", {})
        findings.append({
            "secret_type": item.get("check_id", "unknown"),
            "secret_type_display": meta.get("message"),
            "tool": "semgrep",
            "filename": item.get("path"),
            "commit_sha": None,
            "line_number": item.get("start", {}).get("line"),
            "validity": "unknown",
            "state": "open",
        })
    return findings


# --------------------------------------------------------------------------- #
# Write to DB + alert                                                          #
# --------------------------------------------------------------------------- #

async def scan_repo_secrets(
    db: AsyncSession,
    repository_id: int,
    commit_sha: str,
    repo_path: str,
) -> int:
    findings = run_gitleaks(repo_path)
    findings += run_semgrep(repo_path)

    new_count = 0
    for f in findings:
        result = await db.execute(
            """
            INSERT INTO secret_scan_alert
                (repository_id, secret_type, secret_type_display, tool,
                 filename, commit_sha, line_number, validity, state,
                 created_at, updated_at)
            VALUES
                (:repository_id, :secret_type, :secret_type_display, :tool,
                 :filename, :commit_sha, :line_number, :validity, :state,
                 now(), now())
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            {"repository_id": repository_id, "commit_sha": commit_sha, **f},
        )
        row = result.fetchone()
        if row:
            new_count += 1
            # immediate alert for every new secret finding
            await send_alert(
                level="critical",
                title=f"Secret detected: {f['secret_type']}",
                body=(
                    f"Tool: {f['tool']}\n"
                    f"File: {f['filename']}:{f['line_number']}\n"
                    f"Commit: {f.get('commit_sha', 'N/A')}"
                ),
                metadata={"repository_id": repository_id, "tool": f["tool"]},
            )

    await db.commit()
    logger.info(f"[secrets] repo={repository_id} commit={commit_sha[:7]} new={new_count}")
    return new_count