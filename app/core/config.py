"""Application settings, read from environment variables or .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_env(key: str, default: str = "", required: bool = False) -> str:
    """Read one environment variable, falling back to a default."""
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


class Settings:
    """Typed access to all configured values, one attribute per variable."""
    # App
    APP_ENV: str = _get_env("APP_ENV", "development")
    DEBUG: bool = _get_env("DEBUG", "true").lower() == "true"
    APP_HOST: str = _get_env("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(_get_env("APP_PORT", "8000"))

    # Database
    DATABASE_URL: str = _get_env("DATABASE_URL", "sqlite:///./fleet.db", required=False)

    # Security
    SECRET_KEY: str = _get_env("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = _get_env("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        _get_env("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
    )

    # Auth
    BCRYPT_ROUNDS: int = int(_get_env("BCRYPT_ROUNDS", "12"))


settings = Settings()
