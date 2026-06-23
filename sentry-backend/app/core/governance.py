"""
Governance: presence is not performance.
Caveats are injected into any KPI response that could be misread
as a productivity or performance metric.
"""

CAVEATS = {
    "attendance": (
        "Attendance and presence data measures when people badge in/out. "
        "It does not measure productivity, performance, or output. "
        "Do not use this data to evaluate individual performance."
    ),
    "occupancy": (
        "Occupancy data measures physical space utilisation. "
        "It does not reflect employee performance or engagement. "
        "Do not use this data to evaluate individual performance."
    ),
    "anomaly": (
        "Anomaly scores flag statistical outliers in access patterns. "
        "An anomaly is not evidence of misconduct or poor performance. "
        "Always investigate context before acting on anomaly data."
    ),
    "code_quality": (
        "Code quality metrics measure technical indicators such as churn and complexity. "
        "They do not measure developer productivity or individual performance. "
        "Use these metrics to improve systems, not to evaluate people."
    ),
    "dora": (
        "DORA metrics measure team-level delivery performance. "
        "They are not a measure of individual developer output or value. "
        "Do not use DORA metrics to evaluate individual employees."
    ),
}


def add_caveat(response: dict, domain: str) -> dict:
    """Inject a governance caveat into any KPI response dict."""
    caveat = CAVEATS.get(domain)
    if caveat:
        response["_governance"] = {
            "caveat": caveat,
            "policy": "presence-is-not-performance",
            "domain": domain,
        }
    return response


def add_caveat_to_list(response: list, domain: str) -> dict:
    """Wrap a list response with governance caveat."""
    caveat = CAVEATS.get(domain)
    return {
        "data": response,
        "_governance": {
            "caveat": caveat,
            "policy": "presence-is-not-performance",
            "domain": domain,
        },
    }