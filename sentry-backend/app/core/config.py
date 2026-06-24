from pydantic_settings import BaseSettings
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    APP_NAME: str = "Sentry API"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/github/callback"
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = ""
    FRONTEND_URL: str = "http://localhost:3000"
    REPO_CLONE_BASE_DIR: str = "./repos"

    class Config:
        env_file = str(ENV_FILE)
        extra = "allow"

settings = Settings()
