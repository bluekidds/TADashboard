import asyncio
import os
from typing import Optional, Tuple

from neo4j import GraphDatabase
from sqlalchemy import (
    BIGINT,
    DATE,
    DECIMAL,
    MetaData,
    String,
    Table,
    Column,
    ForeignKey,
)
from sqlalchemy.ext.asyncio import create_async_engine


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


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


def _normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _neo4j_settings() -> Tuple[str, Optional[str], Optional[str]]:
    uri = os.getenv("NEO4J_URI")
    if not uri:
        host = os.getenv("NEO4J_HOST", "localhost")
        port = os.getenv("NEO4J_PORT", "7687")
        uri = f"bolt://{host}:{port}"

    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    if not user and not password:
        auth_env = os.getenv("NEO4J_AUTH")
        if auth_env and auth_env.lower() != "none" and "/" in auth_env:
            user, password = auth_env.split("/", 1)

    return uri, user, password


metadata = MetaData()

stocks = Table(
    "stocks",
    metadata,
    Column("symbol", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("sector", String, nullable=True),
    Column("exchange", String, nullable=False),
)

daily_quotes = Table(
    "daily_quotes",
    metadata,
    Column("date", DATE, primary_key=True),
    Column("symbol", String, ForeignKey("stocks.symbol"), primary_key=True),
    Column("open", DECIMAL, nullable=False),
    Column("high", DECIMAL, nullable=False),
    Column("low", DECIMAL, nullable=False),
    Column("close", DECIMAL, nullable=False),
    Column("volume", BIGINT, nullable=False),
    Column("turnover", BIGINT, nullable=True),
)


async def init_postgres() -> None:
    engine = create_async_engine(_postgres_url(), future=True)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    await engine.dispose()


def init_neo4j() -> None:
    uri, user, password = _neo4j_settings()
    auth = (user, password) if user and password else None
    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as session:
        session.run(
            "CREATE CONSTRAINT stock_symbol_unique IF NOT EXISTS "
            "FOR (s:Stock) REQUIRE s.symbol IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT sector_name_unique IF NOT EXISTS "
            "FOR (s:Sector) REQUIRE s.name IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS "
            "FOR (c:Concept) REQUIRE c.name IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT pattern_identity_unique IF NOT EXISTS "
            "FOR (p:Pattern) REQUIRE (p.type, p.date, p.stage) IS UNIQUE"
        )
    driver.close()


async def main() -> None:
    await init_postgres()
    init_neo4j()


if __name__ == "__main__":
    asyncio.run(main())
