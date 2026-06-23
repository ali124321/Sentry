"""
Observability: structured logging, run metrics, and failure alerting.
"""
import logging
import os
import json
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

# ── Structured Logger ─────────────────────────────────────────────────────────

class StructuredLogger:
    """Wraps standard logger with structured JSON output for each pipeline event."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log(self, level: str, event: str, **kwargs):
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            **kwargs,
        }
        msg = json.dumps(payload)
        getattr(self.logger, level)(msg)

    def info(self, event: str, **kwargs): self.log("info", event, **kwargs)
    def warning(self, event: str, **kwargs): self.log("warning", event, **kwargs)
    def error(self, event: str, **kwargs): self.log("error", event, **kwargs)


pipeline_logger = StructuredLogger("pipeline")


# ── Failure Alerting ──────────────────────────────────────────────────────────

async def send_alert(job_name: str, error: str):
    """
    Send failure alert. Supports Slack webhook (set SLACK_WEBHOOK_URL env var).
    Falls back to structured log if no webhook configured.
    """
    message = f":red_circle: *Pipeline failure*: `{job_name}`\n```{error[:500]}```"

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json={"text": message}, timeout=5)
            pipeline_logger.info("alert_sent", job=job_name, channel="slack")
        except Exception as e:
            pipeline_logger.error("alert_failed", job=job_name, error=str(e))
    else:
        pipeline_logger.error("pipeline_failure_alert", job=job_name, error=error)
        