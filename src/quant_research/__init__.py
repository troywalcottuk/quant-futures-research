"""Research tools for transparent intraday futures backtests."""

from .backtest import BacktestConfig, run_backtest
from .metrics import split_by_date, summarize_trades

__all__ = ["BacktestConfig", "run_backtest", "split_by_date", "summarize_trades"]
__version__ = "0.1.0"
