"""Trade-level metrics and bootstrap uncertainty estimate."""

import numpy as np
import pandas as pd


def bootstrap_mean_ci(values, confidence: float = 0.95, iterations: int = 5000, seed: int = 2026):
    """Percentile bootstrap confidence interval for a sample mean."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return None
    if not 0 < confidence < 1 or iterations < 100:
        raise ValueError("Invalid confidence or too few bootstrap iterations")
    rng = np.random.default_rng(seed)
    sample_means = rng.choice(values, (iterations, len(values)), replace=True).mean(axis=1)
    alpha = (1 - confidence) / 2
    low, high = np.quantile(sample_means, [alpha, 1 - alpha])
    return [float(low), float(high)]


def summarize_trades(trades: pd.DataFrame) -> dict:
    """Summarize net trade outcomes; does not infer account returns."""
    if trades.empty:
        return {
            "trade_count": 0, "win_rate": None, "mean_net_r": None,
            "median_net_r": None, "total_net_pnl_usd": 0.0,
            "profit_factor": None, "max_drawdown_usd": 0.0,
            "mean_net_r_bootstrap_95_ci": None,
        }
    r = pd.to_numeric(trades.net_r, errors="raise").astype(float)
    pnl = pd.to_numeric(trades.net_pnl_usd, errors="raise").astype(float)
    wins, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    equity = pnl.cumsum().to_numpy(float)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])[1:]
    drawdown = equity - peaks
    return {
        "trade_count": int(len(trades)),
        "win_rate": float((r > 0).mean()),
        "mean_net_r": float(r.mean()),
        "median_net_r": float(r.median()),
        "total_net_pnl_usd": float(pnl.sum()),
        "profit_factor": float(wins / losses) if losses > 0 else None,
        "max_drawdown_usd": float(min(0.0, drawdown.min())),
        "mean_net_r_bootstrap_95_ci": bootstrap_mean_ci(r),
    }


def split_by_date(trades: pd.DataFrame, cutoff_date: str):
    """Return pre-cutoff training trades and cutoff-or-later test trades."""
    if trades.empty:
        return trades.copy(), trades.copy()
    cutoff = pd.Timestamp(cutoff_date).date()
    dates = pd.to_datetime(trades.entry_time, utc=True).dt.date
    return (
        trades.loc[dates < cutoff].reset_index(drop=True),
        trades.loc[dates >= cutoff].reset_index(drop=True),
    )
