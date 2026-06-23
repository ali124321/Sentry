from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.core.governance import CAVEATS

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


@router.get("/caveats")
async def get_all_caveats(current_user=Depends(get_current_user)):
    """Return all governance caveats for all KPI domains."""
    return {
        "policy": "presence-is-not-performance",
        "description": (
            "Sentry enforces a governance policy that presence, access, and code metrics "
            "must never be used as proxies for individual performance evaluation."
        ),
        "caveats": CAVEATS,
    }


@router.get("/caveats/{domain}")
async def get_domain_caveat(domain: str, current_user=Depends(get_current_user)):
    """Return governance caveat for a specific domain."""
    if domain not in CAVEATS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No caveat found for domain '{domain}'")
    return {
        "domain": domain,
        "policy": "presence-is-not-performance",
        "caveat": CAVEATS[domain],
    }