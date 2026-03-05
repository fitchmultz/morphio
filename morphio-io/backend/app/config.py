"""Purpose: Centralized runtime configuration for the Morphio backend.
Responsibilities: Load settings from canonical env sources and enforce safety invariants.
Scope: Environment parsing, secret-file overrides, and production guardrails.
Usage: Imported by backend startup and services via `get_settings()`.
Invariants/Assumptions: Only root .env/.env.example are canonical and production secrets must be non-default.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import dotenv_values
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Load canonical .env from monorepo root.
# Resolve by walking up to the nearest .env.example to avoid brittle path depth assumptions.
def _find_monorepo_root(start_dir: Path) -> Path:
    for candidate in [start_dir] + list(start_dir.parents):
        if (candidate / ".env.example").exists():
            return candidate
    return start_dir


config_dir = Path(__file__).resolve().parent
root_env = _find_monorepo_root(config_dir) / ".env"


def _apply_env(path: Path, override: bool) -> None:
    if not path.exists():
        return
    for key, value in dotenv_values(path).items():
        if value in (None, ""):
            continue
        if override or key not in os.environ:
            os.environ[key] = value


_apply_env(root_env, override=False)

# Values that are explicitly invalid for production secrets.
_INVALID_PRODUCTION_SECRET_VALUES = {
    "",
    "dev_secret_key",
    "dev_jwt_secret_key",
    "__GENERATE_SECURE_VALUE__",
    "__CHANGE_ME__",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)
    APP_ENV: str = Field(default="production", json_schema_extra={"env": "APP_ENV"})
    DEBUG: bool = Field(default=False, json_schema_extra={"env": "DEBUG"})
    LOG_LEVEL: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    APP_PORT: int = Field(default=8005, ge=1024, le=65535, json_schema_extra={"env": "APP_PORT"})
    UVICORN_WORKERS: int = Field(default=2, json_schema_extra={"env": "UVICORN_WORKERS"})
    REGISTRATION_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "REGISTRATION_ENABLED"}
    )
    SECRET_KEY: SecretStr = Field(
        default=SecretStr("dev_secret_key"), json_schema_extra={"env": "SECRET_KEY"}
    )
    JWT_SECRET_KEY: str = Field(
        default="dev_jwt_secret_key", json_schema_extra={"env": "JWT_SECRET_KEY"}
    )
    JWT_ALGORITHM: str = Field(default="HS256", json_schema_extra={"env": "JWT_ALGORITHM"})
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, json_schema_extra={"env": "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"}
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, json_schema_extra={"env": "JWT_REFRESH_TOKEN_EXPIRE_DAYS"}
    )

    # Admin user settings
    ADMIN_EMAIL: str = Field(default="admin@morphio.io", json_schema_extra={"env": "ADMIN_EMAIL"})
    ADMIN_PASSWORD: str = Field(default="", json_schema_extra={"env": "ADMIN_PASSWORD"})
    ADMIN_NAME: str = Field(default="Administrator", json_schema_extra={"env": "ADMIN_NAME"})

    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3005",
            "http://localhost:3500",
            "http://frontend:3005",
            "https://morphio.io",
            "http://morphio.io",
            "https://www.morphio.io",
            "https://api.morphio.io",
            "http://api.morphio.io",
        ],
        json_schema_extra={"env": "CORS_ORIGINS"},
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6384/0", json_schema_extra={"env": "REDIS_URL"}
    )
    REDIS_PASSWORD: str = Field(default="", json_schema_extra={"env": "REDIS_PASSWORD"})
    REDIS_DB: int = Field(default=0, json_schema_extra={"env": "REDIS_DB"})
    JOB_CACHE_TTL: int = Field(
        default=3600,
        json_schema_extra={"env": "JOB_CACHE_TTL"},  # 1 hour in seconds
    )
    CACHE_TEMPLATES_TTL_S: int = Field(
        default=300, json_schema_extra={"env": "CACHE_TEMPLATES_TTL_S"}
    )
    CACHE_TEMPLATES_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "CACHE_TEMPLATES_ENABLED"}
    )
    ANTHROPIC_API_KEY: SecretStr = Field(
        default=SecretStr(""), json_schema_extra={"env": "ANTHROPIC_API_KEY"}
    )
    OPENAI_API_KEY: SecretStr = Field(
        default=SecretStr(""), json_schema_extra={"env": "OPENAI_API_KEY"}
    )
    GEMINI_API_KEY: SecretStr = Field(
        default=SecretStr(""), json_schema_extra={"env": "GEMINI_API_KEY"}
    )
    AUDIO_TRANSCRIPTION_MODEL: str = Field(
        default="local", json_schema_extra={"env": "AUDIO_TRANSCRIPTION_MODEL"}
    )
    WHISPER_MODEL: str = Field(default="small", json_schema_extra={"env": "WHISPER_MODEL"})
    WHISPER_MLX_MODEL: str = Field(default="small", json_schema_extra={"env": "WHISPER_MLX_MODEL"})

    # Speaker diarization settings
    DIARIZATION_ENABLED: bool = Field(
        default=False,
        json_schema_extra={"env": "DIARIZATION_ENABLED"},
        description="Global enable/disable for speaker diarization feature",
    )
    DIARIZATION_MODEL: str = Field(
        default="pyannote/speaker-diarization-3.1",
        json_schema_extra={"env": "DIARIZATION_MODEL"},
        description="HuggingFace model ID for pyannote diarization",
    )
    HUGGING_FACE_TOKEN: SecretStr = Field(
        default=SecretStr(""),
        json_schema_extra={"env": "HUGGING_FACE_TOKEN"},
        description="HuggingFace token for pyannote model access",
    )
    DIARIZATION_MIN_SPEAKERS: Optional[int] = Field(
        default=None,
        json_schema_extra={"env": "DIARIZATION_MIN_SPEAKERS"},
        description="Minimum expected number of speakers (optional hint)",
    )
    DIARIZATION_MAX_SPEAKERS: Optional[int] = Field(
        default=None,
        json_schema_extra={"env": "DIARIZATION_MAX_SPEAKERS"},
        description="Maximum expected number of speakers (optional hint)",
    )
    DIARIZATION_USE_SUBPROCESS: bool = Field(
        default=True,
        json_schema_extra={"env": "DIARIZATION_USE_SUBPROCESS"},
        description="Run diarization in subprocess to isolate PyTorch from MLX memory",
    )
    TITLE_GENERATION_MODEL: str = Field(
        default="gemini-3-flash-preview-minimal",
        json_schema_extra={"env": "TITLE_GENERATION_MODEL"},
    )
    CONTENT_MODEL: str = Field(
        default="gemini-3-flash-preview", json_schema_extra={"env": "CONTENT_MODEL"}
    )
    CONTENT_TEMPERATURE: float = Field(
        default=1.0, json_schema_extra={"env": "CONTENT_TEMPERATURE"}
    )
    GEMINI_MEDIA_RESOLUTION: str = Field(
        default="MEDIA_RESOLUTION_UNSPECIFIED",
        json_schema_extra={"env": "GEMINI_MEDIA_RESOLUTION"},
    )
    RATE_LIMITING_ENABLED: bool = Field(
        default=True, json_schema_extra={"env": "RATE_LIMITING_ENABLED"}
    )
    PROMETHEUS_ENABLED: bool = Field(
        default=False,
        validation_alias="PROMETHEUS_ENABLED",
        description="Enable /metrics endpoint for Prometheus scraping",
    )
    USER_ROUTES_RATE_LIMIT: int = Field(
        default=60, json_schema_extra={"env": "USER_ROUTES_RATE_LIMIT"}
    )
    USER_ROUTES_RATE_WINDOW: int = Field(
        default=60, json_schema_extra={"env": "USER_ROUTES_RATE_WINDOW"}
    )
    CSRF_COOKIE_EXPIRE_SECONDS: int = Field(
        default=86400,
        json_schema_extra={"env": "CSRF_COOKIE_EXPIRE_SECONDS"},  # 24 hours
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=3221225472, json_schema_extra={"env": "MAX_UPLOAD_SIZE"}
    )  # 3 GB
    FILE_CHUNK_SIZE: int = Field(
        default=1048576, json_schema_extra={"env": "FILE_CHUNK_SIZE"}
    )  # 1MB chunks
    TEMPLATE_DIR: str = Field(
        default="./templates/",
        json_schema_extra={"env": "TEMPLATE_DIR"},
    )
    UPLOAD_DIR: str = Field(
        default="./uploads/",
        json_schema_extra={"env": "UPLOAD_DIR"},
    )

    # Split into separate video and audio extensions
    ALLOWED_VIDEO_EXTENSIONS: List[str] = Field(
        default=[
            "mp4",
            "avi",
            "mov",
            "wmv",
            "flv",
            "mkv",
            "webm",
            "ogg",
            "3gp",
            "mpeg",
            "mpg",
            "m4v",
        ],
        json_schema_extra={"env": "ALLOWED_VIDEO_EXTENSIONS"},
    )

    ALLOWED_AUDIO_EXTENSIONS: List[str] = Field(
        default=[
            "mp3",
            "wav",
            "m4a",
            "aac",
            "flac",
            "wma",
            "m4p",
        ],
        json_schema_extra={"env": "ALLOWED_AUDIO_EXTENSIONS"},
    )

    STRIPE_SECRET_KEY: SecretStr = Field(
        default=SecretStr(""), json_schema_extra={"env": "STRIPE_SECRET_KEY"}
    )
    STRIPE_WEBHOOK_SECRET: SecretStr = Field(
        default=SecretStr(""), json_schema_extra={"env": "STRIPE_WEBHOOK_SECRET"}
    )
    STRIPE_PRO_PRICE_ID: str = Field(default="", json_schema_extra={"env": "STRIPE_PRO_PRICE_ID"})
    STRIPE_ENTERPRISE_PRICE_ID: str = Field(
        default="", json_schema_extra={"env": "STRIPE_ENTERPRISE_PRICE_ID"}
    )
    FRONTEND_URL: str = Field(
        default="http://localhost:3005", json_schema_extra={"env": "FRONTEND_URL"}
    )

    # Usage weighting and plan-limits
    USAGE_WEIGHTS: Dict[str, int] = Field(
        default={
            "VIDEO_PROCESSING": 2,
            "AUDIO_PROCESSING": 1,
            "WEB_SCRAPING": 1,
            "CONTENT_GENERATION": 2,
            "LOG_PROCESSING": 1,
            "OTHER": 1,
        },
        validation_alias="USAGE_WEIGHTS_JSON",
    )
    SUBSCRIPTION_PLAN_LIMITS: Dict[str, int] = Field(
        default={
            "free": 50,
            "pro": 1000,
            "enterprise": 999999999,
        },
        validation_alias="SUBSCRIPTION_PLAN_LIMITS_JSON",
    )

    ALLOWED_LOG_EXTENSIONS: List[str] = Field(
        default=["csv", "json", "log", "md", "txt"],
        json_schema_extra={"env": "ALLOWED_LOG_EXTENSIONS"},
    )

    # --- Added DB environment variables for easy switching ---
    DB_DIALECT: str = Field(
        default="sqlite", json_schema_extra={"env": "DB_DIALECT"}
    )  # "sqlite" or "postgres"
    DB_HOST: str = Field(default="localhost", json_schema_extra={"env": "DB_HOST"})
    DB_PORT: int = Field(default=5432, json_schema_extra={"env": "DB_PORT"})
    DB_NAME: str = Field(default="morphio", json_schema_extra={"env": "DB_NAME"})
    DB_USER: str = Field(default="morphio", json_schema_extra={"env": "DB_USER"})
    DB_PASSWORD: str = Field(default="", json_schema_extra={"env": "DB_PASSWORD"})

    # External service endpoints (optional)
    WORKER_ML_URL: str = Field(default="", json_schema_extra={"env": "WORKER_ML_URL"})
    CRAWLER_URL: str = Field(default="", json_schema_extra={"env": "CRAWLER_URL"})
    SERVICE_TIMEOUT: int = Field(default=60, json_schema_extra={"env": "SERVICE_TIMEOUT"})
    DATABASE_URL: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("DATABASE_URL", "SQLALCHEMY_DATABASE_URI"),
    )

    @property
    def database_url(self) -> str:
        """
        Determine the effective async database URL used by SQLAlchemy.

        - If `DATABASE_URL` is set, normalize it for async drivers and use it.
        - Else if `DB_DIALECT='postgres'`, build
          postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB_NAME
        - Else use local SQLite (dev default).
        """
        raw = (self.DATABASE_URL.get_secret_value() or "").strip()
        if raw:
            # Normalize Postgres schemes to asyncpg
            if raw.startswith("postgres://"):
                raw = "postgresql+asyncpg://" + raw[len("postgres://") :]
            elif raw.startswith("postgresql://"):
                raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]
            return raw

        if self.DB_DIALECT.lower() == "postgres":
            password = self.DB_PASSWORD
            userinfo = f"{self.DB_USER}:{password}" if password else f"{self.DB_USER}"
            return f"postgresql+asyncpg://{userinfo}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

        # Default to local SQLite for development
        db_path = "./db/morphio_io.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite+aiosqlite:///{db_path}"

    # DEPRECATED: Direct SDK client access is forbidden.
    # Use morphio-core via app/adapters/llm.py instead.
    # See docs/architecture.md for the adapter boundary documentation.

    @property
    def anthropic_client(self):
        raise RuntimeError(
            "DEPRECATED: Direct SDK client access is forbidden. "
            "Use morphio-core via app/adapters/llm.py instead."
        )

    @property
    def openai_client(self):
        raise RuntimeError(
            "DEPRECATED: Direct SDK client access is forbidden. "
            "Use morphio-core via app/adapters/llm.py instead."
        )

    @property
    def gemini_client(self):
        raise RuntimeError(
            "DEPRECATED: Direct SDK client access is forbidden. "
            "Use morphio-core via app/adapters/llm.py instead."
        )

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        d = super().model_dump(*args, **kwargs)
        return d

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Support Docker secrets and *_FILE env overrides
        # Example: set SECRET_KEY_FILE=/run/secrets/SECRET_KEY (or mount /run/secrets/SECRET_KEY)
        def _maybe_read_secret(path: str) -> str | None:
            try:
                if path and os.path.isfile(path):
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read().strip()
            except Exception:
                return None
            return None

        def _apply_file_override(name: str, is_secretstr: bool = False):
            explicit_path = os.getenv(f"{name}_FILE")
            value = _maybe_read_secret(explicit_path) if explicit_path else None
            if value is None:
                value = _maybe_read_secret(f"/run/secrets/{name}")
            if value is not None and value != "":
                if is_secretstr:
                    setattr(self, name, SecretStr(value))
                else:
                    setattr(self, name, value)

        _apply_file_override("SECRET_KEY", is_secretstr=True)
        _apply_file_override("JWT_SECRET_KEY")
        _apply_file_override("STRIPE_SECRET_KEY", is_secretstr=True)
        _apply_file_override("STRIPE_WEBHOOK_SECRET", is_secretstr=True)
        _apply_file_override("OPENAI_API_KEY", is_secretstr=True)
        _apply_file_override("ANTHROPIC_API_KEY", is_secretstr=True)
        _apply_file_override("GEMINI_API_KEY", is_secretstr=True)
        _apply_file_override("HUGGING_FACE_TOKEN", is_secretstr=True)
        _apply_file_override("REDIS_PASSWORD")
        _apply_file_override("REDIS_URL")
        _apply_file_override("DB_PASSWORD")
        _apply_file_override("DATABASE_URL", is_secretstr=True)

        # Enforce non-default, non-placeholder secrets in production.
        if str(self.APP_ENV).lower() == "production":
            secret_key_val = (self.SECRET_KEY.get_secret_value() or "").strip()
            jwt_secret_val = (self.JWT_SECRET_KEY or "").strip()
            if secret_key_val in _INVALID_PRODUCTION_SECRET_VALUES:
                raise RuntimeError(
                    "SECURITY: SECRET_KEY must be set to a strong, non-default value in production."
                )
            if jwt_secret_val in _INVALID_PRODUCTION_SECRET_VALUES:
                raise RuntimeError(
                    "SECURITY: JWT_SECRET_KEY must be set to a strong, non-default value in production."
                )

            # Database hardening for production
            db_url = (self.DATABASE_URL.get_secret_value() or "").strip()
            if not db_url:
                # Require a full connection string in production
                raise RuntimeError(
                    "CONFIG: DATABASE_URL must be set to a PostgreSQL DSN in production"
                )
            if db_url.startswith("sqlite"):
                raise RuntimeError(
                    "CONFIG: SQLite is not allowed in production. Provide a PostgreSQL DATABASE_URL"
                )

            # Set dialect hint for other parts (e.g., connect_args) based on URL
            if db_url.startswith("postgres") or db_url.startswith("postgresql"):
                self.DB_DIALECT = "postgres"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
