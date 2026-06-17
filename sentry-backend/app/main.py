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


@asynccontextmanager
async def lifespan(app: FastAPI):
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

@app.get("/")
async def root():
    return {"message": "Welcome to the Sentry Backend API!"}

@app.get("/health")
async def health():
    return {"status": "ok"}