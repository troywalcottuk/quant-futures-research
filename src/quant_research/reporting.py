"""Small chart helper for reproducible example output."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def save_equity_curve(trades: pd.DataFrame, path: str | Path) -> None:
    """Save cumulative net P&L per contract; the chart is not account return."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    if trades.empty:
        ax.text(0.5, 0.5, "No trades generated", ha="center", va="center")
        ax.set_axis_off()
    else:
        ordered = trades.sort_values("entry_time")
        dates = pd.to_datetime(ordered.entry_time, utc=True)
        ax.plot(dates, ordered.net_pnl_usd.astype(float).cumsum(), color="#176b87")
        ax.axhline(0, color="#555555", linewidth=0.8)
        ax.set_title("Cumulative net P&L per contract")
        ax.set_ylabel("USD")
        ax.set_xlabel("Entry date")
        ax.grid(alpha=0.25)
        fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
