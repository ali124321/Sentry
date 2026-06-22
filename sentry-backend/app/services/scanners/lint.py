"""
SENTRY-32: Lint scanner — runs Ruff (Python) and ESLint (JS/TS)
and writes findings into lint_finding.
"""

import json
import logging
import subprocess
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _run(cmd: list[str], cwd: str) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    return result.stdout


# --------------------------------------------------------------------------- #
# Ruff                                                                         #
# --------------------------------------------------------------------------- #

RUFF_SEVERITY_MAP = {
    "E": "error", "F": "error", "W": "warning",
    "C": "warning", "N": "info", "ANN": "info",
    "S": "error",   # security rules
}


def _ruff_severity(rule_id: str) -> str:
    for prefix, sev in RUFF_SEVERITY_MAP.items():
        if rule_id.startswith(prefix):
            return sev
    return "info"


def run_ruff(repo_path: str, commit_sha: str, repository_id: int) -> list[dict]:
    raw = _run(
        ["ruff", "check", ".", "--output-format", "json", "--quiet"],
        cwd=repo_path,
    )
    if not raw.strip():
        return []

    try:
        results = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("[ruff] failed to parse JSON output")
        return []

    findings = []
    for item in results:
        rule_id = item.get("code") or "unknown"
        findings.append({
            "repository_id": repository_id,
            "commit_sha": commit_sha,
            "filename": item.get("filename", "").replace(repo_path, "").lstrip("/"),
            "line_start": item.get("location", {}).get("row"),
            "line_end": item.get("end_location", {}).get("row"),
            "col_start": item.get("location", {}).get("column"),
            "col_end": item.get("end_location", {}).get("column"),
            "tool": "ruff",
            "rule_id": rule_id,
            "severity": _ruff_severity(rule_id),
            "message": item.get("message"),
            "category": "security" if rule_id.startswith("S") else "style",
            "status": "open",
        })
    return findings


# --------------------------------------------------------------------------- #
# ESLint                                                                       #
# --------------------------------------------------------------------------- #

ESLINT_SEVERITY_MAP = {1: "warning", 2: "error"}


def run_eslint(repo_path: str, commit_sha: str, repository_id: int) -> list[dict]:
    raw = _run(
        ["npx", "eslint", ".", "--format", "json", "--ext", ".js,.ts,.jsx,.tsx"],
        cwd=repo_path,
    )
    if not raw.strip():
        return []

    try:
        results = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("[eslint] failed to parse JSON output")
        return []

    findings = []
    for file_result in results:
        filename = file_result.get("filePath", "").replace(repo_path, "").lstrip("/")
        for msg in file_result.get("messages", []):
            findings.append({
                "repository_id": repository_id,
                "commit_sha": commit_sha,
                "filename": filename,
                "line_start": msg.get("line"),
                "line_end": msg.get("endLine"),
                "col_start": msg.get("column"),
                "col_end": msg.get("endColumn"),
                "tool": "eslint",
                "rule_id": msg.get("ruleId") or "unknown",
                "severity": ESLINT_SEVERITY_MAP.get(msg.get("severity", 1), "warning"),
                "message": msg.get("message"),
                "category": "style",
                "status": "open",
            })
    return findings


# --------------------------------------------------------------------------- #
# Write to DB                                                                  #
# --------------------------------------------------------------------------- #

async def scan_repo_lint(
    db: AsyncSession,
    repository_id: int,
    commit_sha: str,
    repo_path: str,
) -> int:
    findings = run_ruff(repo_path, commit_sha, repository_id)
    findings += run_eslint(repo_path, commit_sha, repository_id)

    for f in findings:
        await db.execute(
            """
            INSERT INTO lint_finding
                (repository_id, commit_sha, filename,
                 line_start, line_end, col_start, col_end,
                 tool, rule_id, severity, message, category, status)
            VALUES
                (:repository_id, :commit_sha, :filename,
                 :line_start, :line_end, :col_start, :col_end,
                 :tool, :rule_id, :severity, :message, :category, :status)
            """,
            f,
        )

    await db.commit()
    logger.info(f"[lint] repo={repository_id} commit={commit_sha[:7]} findings={len(findings)}")
    return len(findings)