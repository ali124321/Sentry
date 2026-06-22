"""
SENTRY-32: Alert dispatcher — sends to Slack and/or email.
Configure ALERT_SLACK_WEBHOOK and ALERT_EMAIL in your .env.
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SLACK_WEBHOOK = os.getenv("ALERT_SLACK_WEBHOOK")
ALERT_LEVEL_EMOJI = {
    "critical": "🚨",
    "warning": "⚠️",
    "info": "ℹ️",
}


async def send_alert(
    level: str,
    title: str,
    body: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    emoji = ALERT_LEVEL_EMOJI.get(level, "🔔")
    message = f"{emoji} *{title}*\n```{body}```"

    if SLACK_WEBHOOK:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(SLACK_WEBHOOK, json={"text": message})
        except Exception as e:
            logger.error(f"[alert] Slack delivery failed: {e}")
    else:
        logger.warning(f"[alert] No ALERT_SLACK_WEBHOOK set — alert dropped: {title}")