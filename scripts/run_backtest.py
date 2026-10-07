"""Run the sample or a user-provided one-minute OHLC CSV."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quant_research import BacktestConfig, run_backtest, split_by_date, summarize_trades
from quant_research.backtest import load_bars
from quant_research.reporting import save_equity_curve


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars", type=Path, default=ROOT / "data" / "sample_1m_ohlc.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "sample_run")
    parser.add_argument("--split-date", default="2024-01-30")
    parser.add_argument("--target-r", type=float, default=2.0)
    parser.add_argument("--slippage-ticks", type=float, default=1.0)
    parser.add_argument("--commission-per-side", type=float, default=0.62)
    args = parser.parse_args()

    config = BacktestConfig(
        target_r=args.target_r,
        slippage_ticks=args.slippage_ticks,
        commission_per_side_usd=args.commission_per_side,
    )
    bars = load_bars(args.bars, config.timezone)
    trades = run_backtest(bars, config)
    train, test = split_by_date(trades, args.split_date)
    report = {
        "strategy": "15-minute opening-range breakout; next-bar-open entry",
        "synthetic_sample": args.bars.resolve() == (ROOT / "data" / "sample_1m_ohlc.csv").resolve(),
        "assumptions": {
            "point_value_usd": config.point_value_usd,
            "tick_size": config.tick_size,
            "slippage_ticks_per_side": config.slippage_ticks,
            "commission_usd_per_side": config.commission_per_side_usd,
        },
        "all": summarize_trades(trades),
        "train_before_cutoff": summarize_trades(train),
        "test_on_or_after_cutoff": summarize_trades(test),
        "split_date": args.split_date,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    trades.to_csv(args.output / "trades.csv", index=False)
    save_equity_curve(trades, args.output / "equity_curve.png")
    (args.output / "summary.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, allow_nan=False))
    print(f"\nSaved outputs to {args.output}")


if __name__ == "__main__":
    main()
