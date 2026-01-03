import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _postgres_url() -> str:
    url = os.getenv("POSTGRES_URL")
    if url:
        return _normalize_postgres_url(url)

    user = _require_env("POSTGRES_USER")
    password = _require_env("POSTGRES_PASSWORD")
    database = _require_env("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    return _normalize_postgres_url(
        f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    )


def get_engine() -> AsyncEngine:
    return create_async_engine(_postgres_url(), future=True)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)
