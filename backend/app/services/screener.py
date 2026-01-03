from __future__ import annotations

import numpy as np
import pandas as pd


def _rolling_slope(series: pd.Series, window: int) -> float:
    if len(series) < window:
        return 0.0
    y = series.tail(window).to_numpy()
    x = np.arange(window)
    slope, _ = np.polyfit(x, y, 1)
    return float(slope)


def check_vcp(df: pd.DataFrame) -> dict[str, bool]:
    required_columns = {"close", "high", "low", "volume"}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.copy()
    df["ma50"] = df["close"].rolling(50).mean()
    df["ma150"] = df["close"].rolling(150).mean()
    df["ma200"] = df["close"].rolling(200).mean()

    latest = df.iloc[-1]
    low_52w = df["low"].tail(252).min()
    high_52w = df["high"].tail(252).max()

    trend_template = all(
        [
            latest["close"] > latest["ma150"],
            latest["close"] > latest["ma200"],
            latest["ma150"] > latest["ma200"],
            latest["close"] > latest["ma50"],
            latest["close"] >= low_52w * 1.3,
            latest["close"] >= high_52w * 0.75,
            _rolling_slope(df["ma200"].dropna(), 20) > 0,
        ]
    )

    recent = df.tail(40)
    contraction_depth = (recent["high"].max() - recent["low"].min()) / recent[
        "high"
    ].max()
    volume_dry_up = recent["volume"].mean() < df["volume"].tail(120).mean()

    return {
        "trend_template": trend_template,
        "contraction_candidate": contraction_depth < 0.25,
        "volume_dry_up": volume_dry_up,
    }
