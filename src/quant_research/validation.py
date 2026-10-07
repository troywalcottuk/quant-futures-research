"""Validation for in-memory OHLC bars."""

import re

import numpy as np
import pandas as pd


def validate_bars(frame: pd.DataFrame, timezone: str) -> pd.DataFrame:
    required = ["timestamp", "open", "high", "low", "close"]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise ValueError(f"Missing OHLC columns: {', '.join(missing)}")
    result = frame[required].copy()
    raw = result.timestamp.astype(str)
    aware = raw.str.contains(re.compile(r"(?:Z|[+-]\d{2}:\d{2})$", re.IGNORECASE))
    if aware.any() and not aware.all():
        raise ValueError("Do not mix timezone-aware and naive timestamps")
    if aware.all():
        result["timestamp"] = pd.to_datetime(result.timestamp, utc=True).dt.tz_convert(timezone)
    else:
        parsed = pd.to_datetime(result.timestamp, errors="raise")
        result["timestamp"] = parsed.dt.tz_localize(
            timezone, ambiguous="raise", nonexistent="raise"
        ) if parsed.dt.tz is None else parsed.dt.tz_convert(timezone)
    for col in ["open", "high", "low", "close"]:
        result[col] = pd.to_numeric(result[col], errors="raise")
    values = result[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("OHLC values must be finite and positive")
    invalid = (
        (result.high < result.low)
        | (result.high < result[["open", "close"]].max(axis=1))
        | (result.low > result[["open", "close"]].min(axis=1))
    )
    if invalid.any():
        raise ValueError("Found inconsistent OHLC values")
    if result.timestamp.duplicated().any():
        raise ValueError("Duplicate timestamps found")
    if not result.timestamp.is_monotonic_increasing:
        raise ValueError("Bars must be chronologically ordered")
    return result.reset_index(drop=True)
