"""
Security hardening: rate limiting, account lockout, secrets validation.
"""
import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Failed Login Tracker (in-memory) ─────────────────────────────────────────

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

_failed_attempts: dict[str, list[datetime]] = defaultdict(list)


def record_failed_login(email: str):
    """Record a failed login attempt for an email."""
    now = datetime.utcnow()
    _failed_attempts[email].append(now)
    # Keep only attempts within the lockout window
    _failed_attempts[email] = [
        t for t in _failed_attempts[email]
        if t > now - timedelta(minutes=LOCKOUT_MINUTES)
    ]
    count = len(_failed_attempts[email])
    logger.warning(f"Failed login for {email} — {count}/{MAX_FAILED_ATTEMPTS} attempts")


def is_locked_out(email: str) -> bool:
    """Return True if the email has exceeded the failed attempt threshold."""
    now = datetime.utcnow()
    recent = [
        t for t in _failed_attempts.get(email, [])
        if t > now - timedelta(minutes=LOCKOUT_MINUTES)
    ]
    return len(recent) >= MAX_FAILED_ATTEMPTS


def clear_failed_logins(email: str):
    """Clear failed attempts on successful login."""
    _failed_attempts.pop(email, None)


# ── Secrets Validation ────────────────────────────────────────────────────────

REQUIRED_SECRETS = [
    "SECRET_KEY",
    "DATABASE_URL",
    "GITHUB_TOKEN",
]

def validate_secrets():
    """
    Check all required environment variables are set at startup.
    Logs a warning for each missing secret — does not crash the app.
    """
    missing = [k for k in REQUIRED_SECRETS if not os.getenv(k)]
    if missing:
        for key in missing:
            logger.warning(f"Missing required secret: {key}")
        logger.warning(f"{len(missing)} secret(s) missing — some features may not work")
    else:
        logger.info("All required secrets present")
    return missing