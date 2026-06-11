from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router as auth_router
from app.routes.protected import router as protected_router

app = FastAPI(
    title="Sentry Backend",
    version="1.0.0",
    description="Sentry Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allows your Next.js frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # add production URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router)
app.include_router(protected_router)

# Base endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to the Sentry Backend API!"}

@app.get("/health")
async def health():
    return {"status": "ok"}