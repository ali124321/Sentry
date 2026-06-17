from pydantic_settings import BaseSettings

class AuthSettings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = ""
    GITHUB_LOCAL_CLONE_PATH: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"

auth_settings = AuthSettings()