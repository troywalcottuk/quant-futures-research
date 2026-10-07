# Quant Futures Research Portfolio

A reproducible intraday futures research project. It implements an inspectable
15-minute opening-range breakout baseline, conservative OHLC fill handling,
configurable trading costs, risk statistics and chronological train/test
reporting.

The included bars are synthetic. Their results are not evidence of a
profitable strategy.

## Research question

What would a simple opening-range breakout rule have recorded under explicit
entry, stop, target, session and cost assumptions?

A trade journal containing realized R-multiple outcomes but no minute OHLC
history cannot reconstruct price-level entries and exits. This repository
therefore keeps its synthetic example separate from any personal trade data.

## Strategy specification

1. Use the first 15 one-minute bars from 09:30 New York time to set the range.
2. Signal long on the first later bar close above the range high; signal short
   on the first close below the range low.
3. Enter at the next one-minute bar open.
4. Put the stop at the opposite opening-range boundary and set a 2R target.
5. Allow at most one entry per session. Close remaining positions at the final
   in-session bar close.
6. Resolve bars that touch both stop and target in favor of the stop. A stop
   gap is filled at the bar open; a target gap is filled at the target.

Default contract economics and costs are illustrative: $5 per point, 0.25-point
tick, one tick slippage per side, and $0.62 commission per side. Change these
to match the contract and broker before interpreting per-contract dollar P&L.

## Included

- OHLC validation for chronological order, duplicates, finite prices and valid
  bar ranges.
- New York session handling and daylight-saving-aware timestamps.
- Next-bar entry to prevent filling at the signal bar close.
- Conservative same-bar stop/target logic and gap-aware stop fills.
- Commission and slippage deductions in net P&L and net R.
- Win rate, mean and median net R, profit factor, trade-level drawdown, and a
  seeded bootstrap interval for mean net R.
- Chronological train/test reporting without tuning on the test window.
- Reproducible synthetic data, a command-line runner and unit tests.

## Quick start

Python 3.10 or newer is required.

~~~sh
python -m pip install -e .
python scripts/generate_sample_data.py
python scripts/run_backtest.py
python -m unittest discover -s tests -v
~~~

The run saves trades.csv, summary.json and equity_curve.png under
reports/sample_run/.

To run your own one-minute bars:

~~~sh
python scripts/run_backtest.py --bars /path/to/your_1m_bars.csv --output reports/my_run
~~~

CSV columns: timestamp, open, high, low, close. Timestamps may be aware or
naive; naive timestamps are assumed to be America/New_York local time. Bars
must be chronological and cover the session being tested. The loader checks
OHLC consistency but does not confirm that a vendor supplied every bar.

Assumptions can be adjusted from the command line:

~~~sh
python scripts/run_backtest.py \
  --target-r 2.0 \
  --slippage-ticks 1.0 \
  --commission-per-side 0.62 \
  --split-date 2024-01-30
~~~

The report labels dates before the cutoff as train and dates on or after as
test. Changing parameters after inspecting the test period makes it no longer
out of sample.

## Example result

The seeded synthetic fixture produces 40 trades: 20 before and 20 on/after the
default split date. With the illustrative costs above, the sample run records
-$59.04 total net P&L per contract and -0.246 mean net R. The 20-trade test
segment records -$63.10 and -0.402 mean net R. This is arbitrary for random-walk
data and says nothing about historical market performance.

## Limitations

- The sample is a seeded random walk with no predictive signal. Do not
  interpret its P&L as market performance.
- This is not an implementation of liquidity sweeps, SMT, order blocks,
  fair-value gaps, BOS or discretionary trade management.
- OHLC bars do not reveal intrabar event order. Stop-first handling is
  conservative, but the engine does not model queue position, latency, partial
  fills, market impact, exchange fees or broker-specific margin.
- Dollar P&L assumes one contract and the configured point value. It is not an
  account return and excludes position sizing, taxes and funding effects.
- A single chronological split is a basic guard, not a substitute for
  walk-forward analysis, robustness checks or independent replication.
- Educational research only; not investment advice.

## Further research

- Add contract-specific economics and a data vendor adapter.
- Add walk-forward evaluation and parameter-stability analysis.
- Compare with a no-trade benchmark and alternative exit rules.
- Build a separate analyzer for trade journals with realized R outcomes; do
  not label those outcomes as a price-level backtest.

## Structure

~~~text
quant-futures-research/
  data/                 Synthetic one-minute OHLC fixture and notes
  reports/              Reproducible example outputs
  scripts/              Data generator and command-line runner
  src/quant_research/   Backtest engine, validation and metrics
  tests/                Execution and statistics tests
~~~

## CV summary

See CV_SUMMARY.md for a concise, accurate project entry. The sample results
come from synthetic data; do not describe them as live or historical trading
performance.

## Tools

Python, pandas, NumPy, Matplotlib, unittest and Git.
