from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Sentry API"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/github/callback"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
