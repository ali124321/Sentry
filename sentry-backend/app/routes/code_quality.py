"""
SENTRY-33: Code Quality KPI API (E1-E5)

E1 — GET /api/code-quality/complexity        Top complex files
E2 — GET /api/code-quality/churn             Top churned files (hotspots)
E3 — GET /api/code-quality/lint              Lint density summary
E4 — GET /api/code-quality/secrets           Open secret/vuln alerts
E5 — GET /api/code-quality/summary           Rolled-up dashboard summary
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import require_role

router = APIRouter(prefix="/api/code-quality", tags=["Code Quality"])


# --------------------------------------------------------------------------- #
# E1 — Complexity: top N most complex files                                   #
# --------------------------------------------------------------------------- #

@router.get("/complexity")
async def get_complexity(
    repository_id: int = Query(...),
    limit: int = Query(50, le=200),
    language: Optional[str] = Query(None),
    min_complexity: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin", "leadership", "manager", "employee")),
):
    """
    E1 — Returns the most complex files for a repository,
    ordered by complexity_score descending.
    """
    filters = ["repository_id = :repository_id"]
    params: dict = {"repository_id": repository_id, "limit": limit}

    if language:
        filters.append("language = :language")
        params["language"] = language

    if min_complexity is not None:
        filters.append("complexity_score >= :min_complexity")
        params["min_complexity"] = min_complexity

    where = " AND ".join(filters)

    rows = await db.execute(
        text(f"""
            SELECT
                filename,
                language,
                complexity_score,
                cognitive_complexity,
                loc,
                functions_count,
                commit_sha,
                snapshotted_at
            FROM code_file_metric
            WHERE {where}
              AND complexity_score IS NOT NULL
            ORDER BY complexity_score DESC
            LIMIT :limit
        """),
        params,
    )

    results = rows.mappings().all()
    return {
        "repository_id": repository_id,
        "count": len(results),
        "files": [dict(r) for r in results],
    }


# --------------------------------------------------------------------------- #
# E2 — Churn: hotspot files (churn × complexity)                              #
# --------------------------------------------------------------------------- #

@router.get("/churn")
async def get_churn(
    repository_id: int = Query(...),
    limit: int = Query(50, le=200),
    window: int = Query(30, description="30 or 90 day window"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin", "leadership", "manager", "employee")),
):
    """
    E2 — Returns hotspot files ranked by churn_complexity_score.
    window=30 uses churn_30d, window=90 uses churn_90d.
    """
    churn_col = "churn_30d" if window == 30 else "churn_90d"
    commit_col = "commit_count_30d" if window == 30 else "commit_count_90d"

    rows = await db.execute(
        text(f"""
            SELECT
                filename,
                language,
                complexity_score,
                {churn_col}            AS churn,
                {commit_col}           AS commit_count,
                distinct_authors_30d   AS distinct_authors,
                churn_complexity_score,
                snapshotted_at
            FROM code_file_metric
            WHERE repository_id = :repository_id
              AND {churn_col} IS NOT NULL
            ORDER BY churn_complexity_score DESC NULLS LAST
            LIMIT :limit
        """),
        {"repository_id": repository_id, "limit": limit},
    )

    results = rows.mappings().all()
    return {
        "repository_id": repository_id,
        "window_days": window,
        "count": len(results),
        "hotspots": [dict(r) for r in results],
    }


# --------------------------------------------------------------------------- #
# E3 — Lint density: findings per file / by tool / by severity                #
# --------------------------------------------------------------------------- #

@router.get("/lint")
async def get_lint(
    repository_id: int = Query(...),
    tool: Optional[str] = Query(None, description="ruff | eslint | pylint etc."),
    severity: Optional[str] = Query(None, description="error | warning | info | hint"),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin", "leadership", "manager", "employee")),
):
    """
    E3 — Lint density: open findings grouped by tool/severity,
    plus top offending files.
    """
    # Summary by tool + severity
    summary_rows = await db.execute(
        text("""
            SELECT
                tool,
                severity,
                category,
                COUNT(*)                 AS finding_count,
                COUNT(DISTINCT filename) AS affected_files,
                COUNT(DISTINCT rule_id)  AS distinct_rules
            FROM lint_finding
            WHERE repository_id = :repository_id
              AND status = 'open'
            GROUP BY tool, severity, category
            ORDER BY finding_count DESC
        """),
        {"repository_id": repository_id},
    )
    summary = [dict(r) for r in summary_rows.mappings().all()]

    # Top offending files
    filters = [
        "repository_id = :repository_id",
        "status = 'open'",
    ]
    params: dict = {"repository_id": repository_id, "limit": limit}

    if tool:
        filters.append("tool = :tool")
        params["tool"] = tool
    if severity:
        filters.append("severity = :severity")
        params["severity"] = severity
    if category:
        filters.append("category = :category")
        params["category"] = category

    where = " AND ".join(filters)

    file_rows = await db.execute(
        text(f"""
            SELECT
                filename,
                COUNT(*)                            AS total_findings,
                COUNT(*) FILTER (WHERE severity = 'error')   AS errors,
                COUNT(*) FILTER (WHERE severity = 'warning') AS warnings,
                COUNT(DISTINCT tool)                AS tools_flagging,
                MAX(ingested_at)                    AS last_seen_at
            FROM lint_finding
            WHERE {where}
            GROUP BY filename
            ORDER BY errors DESC, total_findings DESC
            LIMIT :limit
        """),
        params,
    )
    top_files = [dict(r) for r in file_rows.mappings().all()]

    # Top rules
    rule_rows = await db.execute(
        text(f"""
            SELECT
                tool,
                rule_id,
                severity,
                COUNT(*) AS occurrences,
                COUNT(DISTINCT filename) AS files_affected
            FROM lint_finding
            WHERE {where}
            GROUP BY tool, rule_id, severity
            ORDER BY occurrences DESC
            LIMIT 20
        """),
        params,
    )
    top_rules = [dict(r) for r in rule_rows.mappings().all()]

    return {
        "repository_id": repository_id,
        "summary": summary,
        "top_files": top_files,
        "top_rules": top_rules,
    }


# --------------------------------------------------------------------------- #
# E4 — Secrets / vuln alerts                                                  #
# --------------------------------------------------------------------------- #

@router.get("/secrets")
async def get_secrets(
    repository_id: int = Query(...),
    state: str = Query("open", description="open | resolved | dismissed"),
    tool: Optional[str] = Query(None),
    secret_type: Optional[str] = Query(None),
    validity: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin", "leadership")),
):
    """
    E4 — Open secret/vuln alerts with filtering.
    Restricted to admin and lead roles.
    """
    filters = [
        "repository_id = :repository_id",
        "state = :state",
    ]
    params: dict = {
        "repository_id": repository_id,
        "state": state,
        "limit": limit,
        "offset": offset,
    }

    if tool:
        filters.append("tool = :tool")
        params["tool"] = tool
    if secret_type:
        filters.append("secret_type = :secret_type")
        params["secret_type"] = secret_type
    if validity:
        filters.append("validity = :validity")
        params["validity"] = validity

    where = " AND ".join(filters)

    # Summary counts
    summary_rows = await db.execute(
        text("""
            SELECT
                tool,
                secret_type,
                validity,
                COUNT(*)                             AS alert_count,
                SUM(push_protection_bypassed::int)   AS bypass_count
            FROM secret_scan_alert
            WHERE repository_id = :repository_id
              AND state = :state
            GROUP BY tool, secret_type, validity
            ORDER BY alert_count DESC
        """),
        {"repository_id": repository_id, "state": state},
    )
    summary = [dict(r) for r in summary_rows.mappings().all()]

    # Alert list
    alert_rows = await db.execute(
        text(f"""
            SELECT
                id,
                github_alert_number,
                secret_type,
                secret_type_display,
                tool,
                filename,
                commit_sha,
                line_number,
                validity,
                state,
                push_protection_bypassed,
                created_at,
                updated_at
            FROM secret_scan_alert
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    alerts = [dict(r) for r in alert_rows.mappings().all()]

    # Total count
    count_row = await db.execute(
        text(f"SELECT COUNT(*) FROM secret_scan_alert WHERE {where}"),
        params,
    )
    total = count_row.scalar()

    return {
        "repository_id": repository_id,
        "state": state,
        "total": total,
        "offset": offset,
        "summary": summary,
        "alerts": alerts,
    }


# --------------------------------------------------------------------------- #
# E5 — Dashboard summary: all KPIs rolled up                                  #
# --------------------------------------------------------------------------- #

@router.get("/summary")
async def get_summary(
    repository_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin", "leadership", "manager", "employee")),
):
    """
    E5 — Single endpoint for the dashboard card row.
    Returns rolled-up metrics across complexity, churn, lint and secrets.
    """
    # Complexity stats
    complexity_row = await db.execute(
        text("""
            SELECT
                COUNT(*)                        AS total_files,
                ROUND(AVG(complexity_score), 2) AS avg_complexity,
                MAX(complexity_score)           AS max_complexity,
                COUNT(*) FILTER (WHERE complexity_score > 10) AS high_complexity_files
            FROM code_file_metric
            WHERE repository_id = :repository_id
              AND complexity_score IS NOT NULL
        """),
        {"repository_id": repository_id},
    )
    complexity = dict(complexity_row.mappings().first() or {})

    # Churn stats
    churn_row = await db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE churn_30d > 0)          AS active_files_30d,
                ROUND(AVG(churn_30d), 0)                       AS avg_churn_30d,
                MAX(churn_complexity_score)                     AS max_hotspot_score,
                COUNT(*) FILTER (WHERE churn_complexity_score > 100) AS critical_hotspots
            FROM code_file_metric
            WHERE repository_id = :repository_id
        """),
        {"repository_id": repository_id},
    )
    churn = dict(churn_row.mappings().first() or {})

    # Lint stats
    lint_row = await db.execute(
        text("""
            SELECT
                COUNT(*)                                            AS total_open_findings,
                COUNT(*) FILTER (WHERE severity = 'error')         AS errors,
                COUNT(*) FILTER (WHERE severity = 'warning')       AS warnings,
                COUNT(DISTINCT filename)                            AS files_with_findings,
                COUNT(DISTINCT rule_id)                             AS distinct_rules_violated
            FROM lint_finding
            WHERE repository_id = :repository_id
              AND status = 'open'
        """),
        {"repository_id": repository_id},
    )
    lint = dict(lint_row.mappings().first() or {})

    # Secret stats
    secret_row = await db.execute(
        text("""
            SELECT
                COUNT(*)                                            AS open_alerts,
                COUNT(*) FILTER (WHERE validity = 'active')        AS active_secrets,
                COUNT(*) FILTER (WHERE push_protection_bypassed)   AS bypass_count,
                COUNT(DISTINCT secret_type)                         AS distinct_secret_types
            FROM secret_scan_alert
            WHERE repository_id = :repository_id
              AND state = 'open'
        """),
        {"repository_id": repository_id},
    )
    secrets = dict(secret_row.mappings().first() or {})

    # Overall risk score (0-100)
    # Weighted: secrets 40%, complexity 25%, lint errors 20%, churn 15%
    secret_score = min(40, int(secrets.get("open_alerts") or 0) * 4)
    complexity_score = min(25, int(complexity.get("high_complexity_files") or 0) * 2)
    lint_score = min(20, int(lint.get("errors") or 0) // 5)
    churn_score = min(15, int(churn.get("critical_hotspots") or 0) * 3)
    overall_risk = secret_score + complexity_score + lint_score + churn_score

    return {
        "repository_id": repository_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_risk_score": overall_risk,
        "complexity": complexity,
        "churn": churn,
        "lint": lint,
        "secrets": secrets,
    }