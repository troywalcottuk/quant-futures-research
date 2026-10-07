"""Tests for net trade statistics and date splitting."""

import unittest

import pandas as pd

from quant_research.metrics import bootstrap_mean_ci, split_by_date, summarize_trades


class MetricsTests(unittest.TestCase):
    def test_summary_uses_net_outcomes(self):
        trades = pd.DataFrame({"net_r": [1., -1., .5], "net_pnl_usd": [10., -10., 5.]})
        result = summarize_trades(trades)
        self.assertEqual(result["trade_count"], 3)
        self.assertAlmostEqual(result["win_rate"], 2 / 3)
        self.assertAlmostEqual(result["mean_net_r"], 1 / 6)
        self.assertAlmostEqual(result["profit_factor"], 1.5)
        self.assertAlmostEqual(result["max_drawdown_usd"], -10.)

    def test_cutoff_date_is_in_test_set(self):
        trades = pd.DataFrame({
            "entry_time": pd.to_datetime(["2024-01-02T14:30:00Z", "2024-02-01T14:30:00Z"], utc=True),
            "net_r": [1., -1.], "net_pnl_usd": [5., -5.],
        })
        train, test = split_by_date(trades, "2024-02-01")
        self.assertEqual((len(train), len(test)), (1, 1))

    def test_bootstrap_is_reproducible(self):
        self.assertEqual(bootstrap_mean_ci([.1, -.2, .3], seed=5),
                         bootstrap_mean_ci([.1, -.2, .3], seed=5))


if __name__ == "__main__":
    unittest.main()
