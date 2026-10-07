"""Generate fictional, reproducible one-minute OHLC bars."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "sample_1m_ohlc.csv"
TZ = "America/New_York"


def generate(sessions: int = 40, seed: int = 42) -> pd.DataFrame:
    """Generate random-walk bars for software demonstration only."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2024-01-02", periods=sessions)
    rows = []
    last = 4800.0
    for day in dates:
        start = pd.Timestamp(day.date()).tz_localize(TZ) + pd.Timedelta(hours=9, minutes=30)
        ts = pd.date_range(start, periods=390, freq="min")
        change = rng.normal(0, 0.24, size=len(ts))
        opens = np.r_[last, last + np.cumsum(change[:-1])]
        closes = opens + change
        high = np.maximum(opens, closes) + rng.uniform(0.03, 0.24, len(ts))
        low = np.minimum(opens, closes) - rng.uniform(0.03, 0.24, len(ts))
        rows.extend(zip(ts.astype(str), opens, high, low, closes))
        last = float(closes[-1])
    return pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close"])


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    generate().to_csv(OUTPUT, index=False, float_format="%.5f")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
