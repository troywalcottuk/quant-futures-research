"""Conservative single-position intraday opening-range breakout backtest."""

from dataclasses import dataclass
from datetime import time
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    """Strategy and execution assumptions; defaults are illustrative."""

    opening_range_minutes: int = 15
    session_start: str = "09:30"
    session_end: str = "16:00"
    entry_cutoff: str = "11:00"
    target_r: float = 2.0
    tick_size: float = 0.25
    point_value_usd: float = 5.0
    slippage_ticks: float = 1.0
    commission_per_side_usd: float = 0.62
    timezone: str = "America/New_York"

    def __post_init__(self) -> None:
        if self.opening_range_minutes <= 0 or self.target_r <= 0:
            raise ValueError("Opening range and target R must be positive")
        if self.tick_size <= 0 or self.point_value_usd <= 0:
            raise ValueError("Tick size and point value must be positive")
        if self.slippage_ticks < 0 or self.commission_per_side_usd < 0:
            raise ValueError("Trading costs cannot be negative")
        start, end, cutoff = map(_clock, (self.session_start, self.session_end, self.entry_cutoff))
        if not start < cutoff < end:
            raise ValueError("Require session_start < entry_cutoff < session_end")
        session_minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
        if self.opening_range_minutes >= session_minutes:
            raise ValueError("Opening range must be shorter than the session")


def _clock(value: str) -> time:
    try:
        hour, minute = (int(piece) for piece in value.split(":"))
        return time(hour, minute)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected clock time like 09:30, got {value!r}") from exc


def load_bars(path: str | Path, timezone: str = "America/New_York") -> pd.DataFrame:
    """Load and validate timestamp/open/high/low/close CSV bars."""
    frame = pd.read_csv(path)
    required = ["timestamp", "open", "high", "low", "close"]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise ValueError(f"Missing OHLC columns: {', '.join(missing)}")
    frame = frame[required].copy()
    raw = frame["timestamp"].astype(str)
    aware = raw.str.contains(re.compile(r"(?:Z|[+-]\d{2}:\d{2})$", re.IGNORECASE))
    if aware.any() and not aware.all():
        raise ValueError("Do not mix timezone-aware and naive timestamps")
    if aware.all():
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True).dt.tz_convert(timezone)
    else:
        parsed = pd.to_datetime(frame["timestamp"], errors="raise")
        frame["timestamp"] = parsed.dt.tz_localize(
            timezone, ambiguous="raise", nonexistent="raise"
        ) if parsed.dt.tz is None else parsed.dt.tz_convert(timezone)

    for column in ["open", "high", "low", "close"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    values = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("OHLC values must be finite and positive")
    invalid = (
        (frame.high < frame.low)
        | (frame.high < frame[["open", "close"]].max(axis=1))
        | (frame.low > frame[["open", "close"]].min(axis=1))
    )
    if invalid.any():
        raise ValueError("Found inconsistent OHLC values")
    if frame.timestamp.duplicated().any():
        raise ValueError("Duplicate timestamps found")
    if not frame.timestamp.is_monotonic_increasing:
        raise ValueError("Bars must be chronologically ordered")
    return frame.reset_index(drop=True)


def _exit_on_bar(
    bar: Any, direction: int, stop: float, target: float
) -> tuple[float, str] | None:
    """Use stop-first resolution when a bar touches both levels."""
    if direction == 1:
        if bar.open <= stop:
            return float(bar.open), "stop_gap"
        if bar.open >= target:
            return target, "target_gap"
        stop_hit, target_hit = bar.low <= stop, bar.high >= target
    else:
        if bar.open >= stop:
            return float(bar.open), "stop_gap"
        if bar.open <= target:
            return target, "target_gap"
        stop_hit, target_hit = bar.high >= stop, bar.low <= target
    if stop_hit:
        return stop, "stop_same_bar_ambiguity" if target_hit else "stop"
    if target_hit:
        return target, "target"
    return None


def run_backtest(
    bars: pd.DataFrame, config: BacktestConfig | None = None
) -> pd.DataFrame:
    """Run one opening-range breakout trade at most per session.

    The first N one-minute bars define the range. The first close beyond it
    signals a direction; entry is at the next bar open. The stop is the
    opposite range boundary and target is target_r times initial price risk.
    Incomplete opening ranges are skipped. Positions exit at stop, target, or
    the final in-session close. Same-bar stop/target ambiguity resolves to stop.
    """
    config = config or BacktestConfig()
    frame = bars.copy()
    required = ["timestamp", "open", "high", "low", "close"]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise ValueError(f"Missing OHLC columns: {', '.join(missing)}")
    if frame.empty:
        return pd.DataFrame(columns=_TRADE_COLUMNS)

    # Reuse the CSV validator's checks without requiring an intermediate file.
    from .validation import validate_bars
    frame = validate_bars(frame[required], config.timezone)
    frame["_date"] = frame.timestamp.dt.date
    start, end, cutoff = map(_clock, (config.session_start, config.session_end, config.entry_cutoff))
    range_minutes = start.hour * 60 + start.minute + config.opening_range_minutes
    range_end = time(range_minutes // 60, range_minutes % 60)
    trades = []

    for _, whole_day in frame.groupby("_date", sort=True):
        day = whole_day.loc[
            (whole_day.timestamp.dt.time >= start) & (whole_day.timestamp.dt.time < end)
        ].reset_index(drop=True)
        if day.empty:
            continue
        times = day.timestamp.dt.time
        opening = day.loc[(times >= start) & (times < range_end)]
        if len(opening) != config.opening_range_minutes:
            continue
        range_high, range_low = float(opening.high.max()), float(opening.low.min())
        positions = [
            i for i, ts in enumerate(day.timestamp)
            if range_end <= ts.time() < cutoff
        ]

        for signal_i in positions:
            signal = day.iloc[signal_i]
            direction = 1 if signal.close > range_high else -1 if signal.close < range_low else 0
            if direction == 0:
                continue
            entry_i = signal_i + 1
            if entry_i >= len(day) or day.iloc[entry_i].timestamp.time() >= min(end, cutoff):
                break
            entry_bar = day.iloc[entry_i]
            entry = float(entry_bar.open)
            stop = range_low if direction == 1 else range_high
            if (direction == 1 and entry <= stop) or (direction == -1 and entry >= stop):
                break
            risk_points = abs(entry - stop)
            target = entry + direction * config.target_r * risk_points

            exit_price = None
            reason = None
            exit_time = None
            for j in range(entry_i, len(day)):
                bar = day.iloc[j]
                if bar.timestamp.time() >= end:
                    break
                result = _exit_on_bar(bar, direction, stop, target)
                if result:
                    exit_price, reason = result
                    exit_time = bar.timestamp
                    break
            if exit_price is None:
                eligible = day.loc[day.timestamp.dt.time < end]
                last = eligible.iloc[-1]
                exit_price, reason, exit_time = float(last.close), "session_close", last.timestamp

            gross_points = direction * (exit_price - entry)
            slippage_usd = 2 * config.slippage_ticks * config.tick_size * config.point_value_usd
            commission_usd = 2 * config.commission_per_side_usd
            risk_usd = risk_points * config.point_value_usd
            net_pnl = gross_points * config.point_value_usd - slippage_usd - commission_usd
            trades.append({
                "session_date": signal.timestamp.date().isoformat(),
                "direction": "long" if direction == 1 else "short",
                "signal_time": signal.timestamp,
                "entry_time": entry_bar.timestamp,
                "exit_time": exit_time,
                "entry_price": entry,
                "stop_price": stop,
                "target_price": target,
                "exit_price": exit_price,
                "exit_reason": reason,
                "risk_points": risk_points,
                "gross_pnl_points": gross_points,
                "slippage_cost_usd": slippage_usd,
                "commission_usd": commission_usd,
                "risk_usd": risk_usd,
                "net_pnl_usd": net_pnl,
                "net_r": net_pnl / risk_usd,
            })
            break

    return pd.DataFrame(trades, columns=_TRADE_COLUMNS).sort_values(
        "entry_time", ignore_index=True
    ) if trades else pd.DataFrame(columns=_TRADE_COLUMNS)


_TRADE_COLUMNS = [
    "session_date", "direction", "signal_time", "entry_time", "exit_time",
    "entry_price", "stop_price", "target_price", "exit_price", "exit_reason",
    "risk_points", "gross_pnl_points", "slippage_cost_usd", "commission_usd",
    "risk_usd", "net_pnl_usd", "net_r",
]
