"""Behavior tests for execution timing, costs and ambiguous bars."""

import unittest

import pandas as pd

from quant_research import BacktestConfig, run_backtest

TZ = "America/New_York"


def day_bars(last):
    rows = []
    for ts in pd.date_range("2024-01-02 09:30", periods=15, freq="min", tz=TZ):
        rows.append({"timestamp": ts, "open": 100., "high": 101., "low": 99., "close": 100.})
    rows.extend([
        {"timestamp": pd.Timestamp("2024-01-02 09:45", tz=TZ),
         "open": 100., "high": 101.25, "low": 99.9, "close": 101.25},
        {"timestamp": pd.Timestamp("2024-01-02 09:46", tz=TZ),
         "open": 101.25, "high": 101.5, "low": 101., "close": 101.3},
        {"timestamp": pd.Timestamp("2024-01-02 09:47", tz=TZ), **last},
    ])
    return pd.DataFrame(rows)


class BacktestTests(unittest.TestCase):
    def test_next_bar_entry_and_target_exit(self):
        bars = day_bars({"open": 101.3, "high": 105.8, "low": 101.2, "close": 105.})
        config = BacktestConfig(slippage_ticks=0, commission_per_side_usd=0)
        trade = run_backtest(bars, config).iloc[0]
        self.assertEqual(trade.entry_time, pd.Timestamp("2024-01-02 09:46", tz=TZ))
        self.assertEqual(trade.exit_reason, "target")
        self.assertAlmostEqual(trade.net_r, 2.0)

    def test_stop_first_on_ambiguous_bar(self):
        bars = day_bars({"open": 101.3, "high": 106., "low": 98., "close": 102.})
        config = BacktestConfig(slippage_ticks=0, commission_per_side_usd=0)
        trade = run_backtest(bars, config).iloc[0]
        self.assertEqual(trade.exit_reason, "stop_same_bar_ambiguity")
        self.assertAlmostEqual(trade.net_r, -1.0)

    def test_costs_reduce_net_result(self):
        bars = day_bars({"open": 101.3, "high": 105.8, "low": 101.2, "close": 105.})
        free = run_backtest(bars, BacktestConfig(slippage_ticks=0, commission_per_side_usd=0)).iloc[0]
        costs = run_backtest(bars, BacktestConfig(slippage_ticks=1, commission_per_side_usd=.62)).iloc[0]
        self.assertLess(costs.net_pnl_usd, free.net_pnl_usd)
        self.assertLess(costs.net_r, free.net_r)

    def test_next_bar_entry_at_cutoff_is_skipped(self):
        bars = day_bars({"open": 101.3, "high": 105.8, "low": 101.2, "close": 105.})
        config = BacktestConfig(
            entry_cutoff="09:46",
            slippage_ticks=0,
            commission_per_side_usd=0,
        )
        self.assertTrue(run_backtest(bars, config).empty)

    def test_incomplete_opening_range_is_skipped(self):
        bars = day_bars({"open": 101.3, "high": 105.8, "low": 101.2, "close": 105.}).drop(index=4)
        self.assertTrue(run_backtest(bars).empty)


if __name__ == "__main__":
    unittest.main()
