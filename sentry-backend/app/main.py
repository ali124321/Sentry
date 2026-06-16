from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router as auth_router
from app.routes.protected import router as protected_router
from app.routes.user import router as users_router

app = FastAPI(
    title="Sentry Backend",
    version="1.0.0",
    description="Sentry Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
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

@app.get("/")
async def root():
    return {"message": "Welcome to the Sentry Backend API!"}

@app.get("/health")
async def health():
    return {"status": "ok"}