# Independent SPY / SSO strategy research

This candidate aims for a higher long-run return than SPY buy and hold while
keeping its development-period drawdown within SPY's historical drawdown. It is
an exploratory historical result, not a promise of future excess returns. The
production QQQ strategy and Cloudflare pipeline are unchanged.

## Run

Use the repository's Python environment and existing `requirements.txt`:

```bash
python -m pip install -r requirements.txt
python -m spy_strategy backtest --refresh
```

Run from the repository root. Open `spy_strategy/output/spy_report.html` for the
standalone English/Chinese report. It embeds its data and uses the same pinned,
integrity-checked Chart.js CDN as the QQQ report. Tables remain available if the
CDN is unavailable. For a local HTTP server:

```bash
python -m http.server 8765 --directory spy_strategy/output
```

`backtest` always uses the frozen `spy_strategy/selected.json`; it never optimizes
live parameters. The terminal and report show the latest close and next-open
target. A 1.5x target means 50% SPY + 50% SSO, not borrowing another 50% against
SSO. A 0.75x target means 75% SPY + 25% cash.

```bash
# Download and validate only; no optimization.
python -m spy_strategy prepare --refresh

# Reuse cached data for this exact completed trading session.
python -m spy_strategy backtest --as-of 2026-11-04

# Repeat the complete exploratory grid (a few minutes).
python -m spy_strategy research --phase extended

# Repeat the initial, more defensive 144-configuration grid.
python -m spy_strategy research --phase initial
```

`research` writes a new `output/selection.json` and evaluation; it does not replace
the reviewed `selected.json`. An explicit `--config PATH` chooses another frozen
configuration for `backtest`. Use a different `--output PATH` to retain separate
experiments. Cached data are reused unless `--refresh` is supplied; stale ETF
caches fail rather than silently backtest an outdated cutoff. Pin `--as-of` when
comparing parameter sets. Yahoo can revise adjusted historical prices, so even
the same cutoff can differ after a fresh download.

## Selected core/trend rule

The canonical parameters are in `selected.json`; allocation logic is in
`strategy.py`, shared by research, backtesting and the latest signal.

1. Keep an unleveraged 0.75x SPY core. Warm up indicators from SPY's 1993 listing;
   start executable performance on 1995-01-03 for every candidate and benchmark.
2. The macro gate uses SMA250. Exit the bullish state below the average; after
   exit, require a close strictly more than 1% above it to re-enter. Evolve this
   state over complete history.
3. In a bullish regime, set the base target to 1.5x if SMA250 is above its value
   20 sessions earlier and 20-day annualized volatility is below 35%; otherwise
   use 1.0x. A bearish regime uses the 0.75x core.
4. Scale only exposure above the core:
   `raw = 0.75 + (base - 0.75) * min(1, 0.20 / realized_volatility)`.
   The core remains invested even during high volatility. Unlike the QQQ rule,
   MACD/RSI/Supertrend and oversold-floor logic do not select this model's exposure.
5. A close above `SMA250 * 1.15` latches a 1x raw cap; release at or below
   `SMA250 * 1.10`. This uses the shared overheat state and fast confirmation cut.
6. Round to 0.05x, require three identical signatures except for the shared fast
   overheat cut, then apply a 0.15x deadband. Ordinary risk reductions also wait
   for confirmation. Signals at close T trade at the open of T+1.
7. Rebalance only when the target changes; let holdings drift otherwise. The
   1.5x maximum is a target limit, not an absolute limit on realized exposure.

## Data and execution

SPY/SSO adjusted OHLC includes distributions; real ETF expenses are already
embedded. Data stop at the latest NYSE session whose close was at least one hour
ago, including holidays and early closes. Both ETFs must reach that cutoff.
Missing post-inception SSO bars fail validation; they are never synthesized.

Before complete SSO opening splits exist on 2006-06-22, synthetic SSO daily return
is `2 * SPY_return - (0.0095 + prior_IRX / 100) / 252`. Synthetic overnight return
is twice SPY overnight return; intraday is inferred to compound exactly to the
synthetic daily return. This is a financing approximation, not a tradable fund
before inception. Read actual-SSO-only results separately.

The adapter deliberately maps SPY/SSO onto the shared engine's legacy `qqq_*` and
`qld_*` return columns. Existing holdings receive the overnight move, opening
trades pay 5bp per side, and new holdings receive intraday returns. Cash uses the
previously available IRX yield, without future-yield backfill. Taxes and variable
spreads are not modeled. Benchmarks pay the same initial trading cost.

Period metrics include the first daily return relative to prior closing capital;
portfolios carry holdings across period boundaries. The static 50/50 SPY/SSO
comparison buys once and drifts; it is not a constant-daily-leverage benchmark.

## Validation and artifacts

See the [dated research review](../research/SPY_STRATEGY_REVIEW_2026-11-05.md) for
selection, the adaptive research disclosure, exact comparisons and limitations.
Training is 1995–2009, validation/selection 2010–2018, and retrospective testing
2019 onward. Do not call the latter an untouched forward sample.

The ignored `output/` contains raw CSVs with SHA-256 provenance, `prices.csv`,
`data_manifest.json`, the complete development scan, the selection, `results.json`,
`equity.csv`, `signals.csv` and `spy_report.html`. The tracked results snapshot in
`research/` preserves compact metrics without committing market-data caches.

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/worker.test.mjs
```

Tests cover NYSE publication boundaries, prior-yield funding, exact synthetic
compounding, real-SSO gaps, causal prefix signals, next-open execution, position
drift, first-period metrics and invariance of selection to future test prices.
