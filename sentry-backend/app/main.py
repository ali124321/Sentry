from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router as auth_router
from app.routes.protected import router as protected_router
from app.routes.user import router as users_router
from app.routes.ingest import router as ingest_router
from app.routes.identity_qa import router as identity_qa_router
from app.routes.github_auth import router as github_auth_router
from app.routes.github_sync import router as github_sync_router
from app.routes.sync_status import router as sync_status_router
from app.services.sync_job import start_scheduler, stop_scheduler
from contextlib import asynccontextmanager
from app.routes.attendance import router as attendance_router
from app.routes.attendance_kpi import router as attendance_kpi_router
from app.routes.occupancy import router as occupancy_router
from app.routes.occupancy_kpi import router as occupancy_kpi_router
from app.routes.anomaly import router as anomaly_router
from app.routes.security import router as security_router
from app.routes.code_quality import router as code_quality_router
from app.routes.code_quality_actions import router as code_quality_actions_router
from app.routes.dora import router as dora_router
from app.routes.dora_kpi import router as dora_kpi_router
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db
from app.routes.defect_risk import router as defect_risk_router
from app.routes.suppression_test import router as suppression_router
from app.routes.ml_framework import router as ml_framework_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter
from app.core.security import validate_secrets

router = APIRouter(prefix="/api/v1/defect-risk", tags=["defect-risk"])


@router.post("/run")
async def run_defect_risk_model(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """E6 — Train the defect-risk model and score every file in code_file_metric."""
    from app.pipeline.defect_risk_model import run_defect_prediction
    result = await run_defect_prediction(db)
    return result


@router.get("/scores")
async def get_defect_risk_scores(
    repository_id: int = None,
    min_score: float = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get files ranked by defect risk score, highest first."""
    query = """
        SELECT filename, repository_id, defect_risk_score, defect_risk_label,
               churn_30d, complexity_score, distinct_authors_30d, defect_risk_scored_at
        FROM code_file_metric
        WHERE defect_risk_score IS NOT NULL
    """
    params = {"limit": limit}
    if repository_id:
        query += " AND repository_id = :repository_id"
        params["repository_id"] = repository_id
    if min_score is not None:
        query += " AND defect_risk_score >= :min_score"
        params["min_score"] = min_score
    query += " ORDER BY defect_risk_score DESC LIMIT :limit"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "filename": row.filename,
            "repository_id": row.repository_id,
            "defect_risk_score": float(row.defect_risk_score) if row.defect_risk_score is not None else None,
            "defect_risk_label": row.defect_risk_label,
            "churn_30d": row.churn_30d,
            "complexity_score": float(row.complexity_score) if row.complexity_score is not None else None,
            "distinct_authors_30d": row.distinct_authors_30d,
            "scored_at": str(row.defect_risk_scored_at) if row.defect_risk_scored_at else None,
        }
        for row in rows
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_secrets()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Sentry Backend",
    version="1.0.0",
    description="Sentry Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(protected_router)
app.include_router(users_router)
app.include_router(ingest_router)
app.include_router(identity_qa_router)
app.include_router(github_auth_router)
app.include_router(github_sync_router)
app.include_router(sync_status_router)
app.include_router(attendance_router)
app.include_router(attendance_kpi_router)
app.include_router(occupancy_router)
app.include_router(occupancy_kpi_router)
app.include_router(anomaly_router)
app.include_router(security_router)
app.include_router(code_quality_router)
app.include_router(code_quality_actions_router)
app.include_router(dora_router)
app.include_router(dora_kpi_router)
app.include_router(defect_risk_router)
app.include_router(suppression_router)
app.include_router(ml_framework_router)


@app.get("/")
async def root():
    return {"message": "Welcome to the Sentry Backend API!"}


@app.get("/health")
async def health():
    return {"status": "ok"}