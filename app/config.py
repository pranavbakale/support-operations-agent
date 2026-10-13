import os
from dataclasses import dataclass
from functools import lru_cache


def _positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    redis_url: str
    approval_ttl_seconds: int
    policy_top_k: int
    log_level: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv(
            "DATABASE_URL", "postgresql+asyncpg://support:support@localhost:5432/support"
        ),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        approval_ttl_seconds=_positive_int("APPROVAL_TTL_SECONDS", 900),
        policy_top_k=_positive_int("POLICY_TOP_K", 3),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
