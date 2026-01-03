import asyncio
import os
from datetime import date
from typing import Iterable

import pandas as pd
import shioaji as sj
from sqlalchemy.dialects.postgresql import insert

from backend.app.db import init_db
from backend.app.db.postgres import get_engine


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _create_api() -> sj.Shioaji:
    api_key = _require_env("SHIOAJI_API_KEY")
    secret_key = _require_env("SHIOAJI_SECRET_KEY")
    api = sj.Shioaji()
    api.login(api_key=api_key, secret_key=secret_key)
    return api


def _chunk_records(records: list[dict], batch_size: int) -> Iterable[list[dict]]:
    batch: list[dict] = []
    for item in records:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


async def sync_history(
    symbol: str, years: int = 20, sleep_seconds: float = 0.5
) -> int:
    api = _create_api()
    contract = api.Contracts.Stocks.TSE[symbol]
    start_date = date.today().replace(year=date.today().year - years)
    kbars = api.kbars(contract, start=start_date)
    df = pd.DataFrame({**kbars})
    if df.empty:
        return 0

    df["symbol"] = symbol
    df.rename(columns={"ts": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    records = df[
        ["date", "symbol", "Open", "High", "Low", "Close", "Volume", "Amount"]
    ].rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
            "Amount": "turnover",
        }
    )

    inserted = 0
    engine = get_engine()
    for batch in _chunk_records(records.to_dict("records"), batch_size=200):
        statement = insert(init_db.daily_quotes).values(batch)
        statement = statement.on_conflict_do_nothing(
            index_elements=["date", "symbol"]
        )
        async with engine.begin() as conn:
            result = await conn.execute(statement)
            inserted += result.rowcount or 0
        await asyncio.sleep(sleep_seconds)

    return inserted
