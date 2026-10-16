# R Recovery Confirmation Review — 2026-10-16

## Decision and scope

The user requested a separate V1.8.0 PR for R-tier increases bypassing three-day confirmation. This implements only the previously compared `R_fast_1` candidate. The user merges manually.

An R close with a rounded raw exposure above internal confirmed exposure raises that state immediately. Retain the original counter for ordinary three-identical-signature confirmation. R decreases and all other changes retain confirmation, except the existing fast overheat cut. The cap applies after a fast increase and has priority. Retain R base 0.75x, volatility scaling, oversold floor, E/F precedence, macro gate, leverage limits, 0.05 rounding, the 0.15x deadband and next-open execution. This does not introduce an earlier reversal signal, a higher R floor, a smaller deadband, same-close execution or faster B/C entry.

The helper updates internal confirmation state itself, so leaving R does not resurrect an older state. The deadband can still suppress an otherwise fast increase. If existing confirmed exposure is higher than the current R raw target, R does not force an immediate reduction. All four entrypoints share this behavior; indicator ablations use their surviving recovery checks with strong-bear priority.

## Data and methodology

The original discussion used prices through **2026-09-25**. The PR also downloads a fresh, isolated cache through **2026-10-15**. Data cutoffs and metric conventions are explicit below; differing cutoffs are not strategy improvements.

Signals and state evolve over full history, then target weights shift to the next open and trading starts on 1999-03-11. Both portfolios call shared `execution.run_next_open()`: old holdings receive overnight moves and cash interest, the next opening rebalance incurs costs, and new holdings receive intraday moves. Holdings drift when targets do not change. Costs are 5bp per side. Pre-2006 QLD is synthetic; NDX warm-up returns are excluded.

Research subperiods include the first daily return against prior closing capital and include initial capital in drawdown. Production subperiods retain first-close rebasing. Calendar-year returns use previous year-end capital. These are researched-history comparisons, not untouched out-of-sample tests. No new parameter search was conducted.

## Fresh same-cache comparison through 2026-10-15

| Metric | V1.7.0 | V1.8.0 |
|---|---:|---:|
| Full CAGR | 15.47% | 15.50% |
| Full total return | 5159.41% | 5196.12% |
| Full maximum drawdown | -22.44% | -22.97% |
| Since-2006 CAGR | 17.98% | 18.09% |
| Since-2010 CAGR | 18.87% | 18.98% |
| Recent-five-year CAGR | 18.93% | 18.88% |
| Recent-five-year maximum drawdown | -19.60% | -19.95% |
| 2005 calendar-year return | -4.74% | -3.95% |
| 2025 calendar-year return | 12.99% | 14.74% |
| Full Calmar | 0.689 | 0.675 |
| Annual one-way turnover | 6.89x | 6.95x |
| Annual nonzero opening rebalances | 11.40 | 11.87 |

Higher full CAGR and 2005/2025 returns do not imply universally better performance. Full maximum drawdown deepens by about 0.53 percentage points, full Calmar falls, and recent CAGR is slightly lower. The V1.8.0 production-export full CAGR/drawdown/Calmar is **15.50% / -22.97% / 0.675**; recent production CAGR/drawdown is **18.73% / -19.95%**, versus research CAGR **18.88%** on the same fresh cache. The production definition is unchanged.

## Original discussion cache through 2026-09-25

| Metric | V1.7.0 | V1.8.0 |
|---|---:|---:|
| Full CAGR | 15.56% | 15.59% |
| Full maximum drawdown | -22.44% | -22.97% |
| Recent CAGR | 18.81% | 18.76% |
| 2005 return | -4.74% | -3.95% |
| 2025 return | 12.99% | 14.74% |

## Chronological checks on the fresh cache

Cells are CAGR / within-period maximum drawdown, using continuous historical state and holdings. These blocks reuse known history and are not independent validation.

| Period | V1.7.0 | V1.8.0 |
|---|---:|---:|
| 1999-03-11/2010-12-31 | 11.55% / -22.36% | 11.48% / -22.97% |
| 2011-01-01/2014-12-31 | 20.19% / -19.57% | 20.30% / -20.08% |
| 2015-01-01/2018-12-31 | 10.72% / -17.35% | 10.97% / -17.20% |
| 2019-01-01/2022-12-31 | 15.28% / -22.44% | 15.53% / -22.44% |
| 2023-01-01/2026-10-15 | 29.12% / -18.19% | 28.91% / -18.19% |

## Cost and timing sensitivity on the fresh cache

Cells are full CAGR / maximum drawdown. Both portfolios receive the same cost or timing perturbation.

| Scenario | V1.7.0 | V1.8.0 |
|---|---:|---:|
| Normal next-open execution, 5bp | 15.47% / -22.44% | 15.50% / -22.97% |
| Doubled costs, 10bp | 15.07% / -22.57% | 15.10% / -23.18% |
| One extra execution day, 5bp | 15.54% / -22.01% | 15.40% / -22.88% |

The small full-CAGR advantage survives doubled costs, but reverses under one extra execution day. Delays improving some backtests are not a reason to intentionally delay execution. The evidence supports faster participation in the selected rebound examples, not a stable improvement in risk-adjusted performance.

## 2005 and 2025 diagnostics

In 2005, MACD histogram is already positive on May 2 while Supertrend remains bearish; R begins only on May 16 and lasts two closes before B begins on May 18. V1.7.0 never executes its R target in that episode; the new B target restarts confirmation and executes on May 23. Fast R allows 0.75x from the May 17 open instead of remaining near 0.5x. On the original discussion cache, the descriptive April 20 close–July 29 close rebound is QQQ +14.17%, baseline +10.41%, fast R +11.32%. Full-year return improves from -4.74% to -3.95%. January and June losses also contribute to the full-year lag; fast R cannot repair every part of the year.

In 2025, R begins on April 25 with annualized volatility about 61%, compressing its 0.75x base to about 0.25x. The existing 0.15x deadband still blocks a move from 0.15x to 0.25x. It remains intentionally unchanged. Fast R improves later recovery participation; it does not capture an earlier jump before R is known. The April 8 close–June 30 close rebound on the discussion cache is QQQ +32.74%, baseline +15.53%, fast R +17.31%. Both windows use retrospectively selected lows only as diagnostics, never as trading inputs.

## Validation and reproduction

```sh
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/worker.test.mjs
python scripts/research_r_recovery.py
# For a separate freshly downloaded prices.csv:
python scripts/research_r_recovery.py --data-dir /path/to/cache
```

The comparison script stops before production exports and asserts that its fast candidate weights and equity exactly reproduce the current backtest. It never downloads or overwrites production report data. Tests cover R-only fast increases, unchanged decreases and non-R confirmation, cap priority, prefix causality, deadband blocking, full-history next-open shifts and parity among backtest, daily check, optimization and full ablation. The existing cap and deploy tests remain intact. `daily_check.py` is exercised with mocked downloads rather than making CI depend on live market data.

Discussion-cache SHA-256: `7f053199ab5ba1a10606ecbe0d65ba6028ebf336e7c608807efd3a0ec8a6092d`.

Fresh-cache SHA-256: `c2a7eb8b95bbcdea69d607fa2ce03491a8907da2847818575db619d96ee2a5fd`.

Historical research cannot guarantee future returns. These calculations retain the existing synthetic-QLD, transaction-cost and live-execution limitations.
