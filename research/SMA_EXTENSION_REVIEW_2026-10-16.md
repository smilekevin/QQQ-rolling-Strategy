# SMA Extension Cap Adoption Study

Study date: 2026-10-16. Research price cutoff: **2026-09-25**. The user adopted the **SMA250 +15% cap with existing confirmation** as strategy/report **V1.7.0**. This supersedes the earlier decision to retain V1.6.1 only for this rule; other research candidates remain unadopted.

## Adopted rule

Calculate extension as `QQQ adjusted close / SMA250 - 1`. If it is **strictly greater than 15%**, cap the existing **volatility-scaled raw target** at **1x**, then run the original 0.05 rounding, three-consecutive-day confirmation and 0.15x deadband. Raw targets at or below 1x stay unchanged at this stage. When extension returns to 15% or less, the original leverage rules resume through the same confirmation process.

The rule does not change macro state, momentum score, B/C decision tiers, `lever_ok`, the oversold latch or next-open execution. B can therefore still describe an uptrend with a capped 1x target. It is not an immediate overlay on confirmed targets, nor a continuous hard exposure ceiling. Confirmed holdings may lag current extension; weights drift between trades. Recomputing the confirmation path can also occasionally result in a higher target than the original strategy on a later day.

Signals form at T close. Existing holdings absorb the next overnight return and cash interest, rebalance at the T+1 open with 5bp per side, then new holdings earn intraday returns. Execution remains shared in `execution.run_next_open()`.

## Threshold comparison

Each cell is CAGR / maximum drawdown. Research subperiods include the first daily return against prior closing capital, and include starting capital in drawdown. Last five years: 2021-09-27 through 2026-09-25. All indicators, confirmation and holdings retain full-history state.

| Rule | Full period since 1999 | Actual QLD since June 2006 | Since 2010 | Last five years |
|---|---:|---:|---:|---:|
| V1.6.1 baseline | 15.21% / -26.91% | 17.65% / -26.91% | 18.79% / -26.91% | 17.92% / -21.84% |
| SMA250 +10% | 14.70% / -22.44% | 16.72% / -22.44% | 17.31% / -22.44% | 16.09% / -20.96% |
| **SMA250 +15% (adopted)** | **15.66% / -22.44%** | **18.10% / -22.44%** | **19.11% / -22.44%** | **19.27% / -19.60%** |
| SMA250 +20% | 15.67% / -25.46% | 18.12% / -25.46% | 19.42% / -22.44% | 18.94% / -21.84% |
| SMA250 +25% | 15.53% / -26.91% | 17.94% / -26.91% | 19.03% / -26.91% | 18.12% / -21.84% |
| SMA250 +30% | 15.34% / -26.91% | 17.82% / -26.91% | 19.01% / -26.91% | 17.92% / -21.84% |
| SMA250 +40% | 15.21% / -26.91% | 17.65% / -26.91% | 18.79% / -26.91% | 17.92% / -21.84% |

The unchanged production report rebases each subperiod at its first close; this differs from the research convention. On the same cache, V1.7.0's production recent CAGR is **19.46%**, rather than research **19.27%**. The production method was not changed in this release. Live deployments download new data and will differ from this dated snapshot.

## Shorter moving averages

The macro SMA250 gate is preserved; only the extension measure changes. Every SMA20/SMA50 candidate used the same confirmation and execution. A fixed grid tested **2%, 3%, 5%, 7.5%, 10%, 15%, 20%, 25%** for each average, rather than giving short averages only the larger SMA250 thresholds.

| Extension rule | Since-2010 CAGR / drawdown | Last-five-year CAGR / drawdown |
|---|---:|---:|
| SMA20 +5% | 18.88% / -26.91% | 17.24% / -21.79% |
| SMA20 +10% | 18.79% / -26.91% | 17.92% / -21.84% |
| SMA20 +15% or +20% | 18.79% / -26.91% | 17.92% / -21.84% |
| SMA50 +5% | 17.99% / -22.44% | 16.64% / -19.60% |
| SMA50 +10% | 18.94% / -26.91% | 17.94% / -21.84% |
| SMA50 +15% or +20% | 18.79% / -26.91% | 17.92% / -21.84% |

A second comparison matched **training-period raw trigger frequency** among targets above 1x in 2006-06-22 through 2012-12-31, without using future returns. Locking thresholds matching SMA250 +20% gives SMA20 **3.82156%**, SMA50 **7.57172%**, SMA250 **20%**. Since-2013 CAGR is respectively **19.73%, 19.59%, 20.57%**. Matching the +15% anchor also favors SMA250. Future trigger rates need not match. These chronological comparisons are not independent untouched out-of-sample proof because the broader strategy and anchors already use known history.

## Trading frequency

Count actual nonzero opening rebalances, including initial entry, in the unchanged shared execution engine. Selling QLD and buying QQQ is **one rebalance, two security orders**. Annualization uses trading days / 252.

| Period | Baseline rebalances | Adopted rule rebalances | Baseline / adopted annual rebalances | Baseline / adopted orders | Baseline / adopted annual turnover |
|---|---:|---:|---:|---:|---:|
| Since 1999 | 359 | 334 | 13.06 / 12.15 | 578 / 511 | 8.41x / 7.60x |
| Since 2010 | 237 | 216 | 14.19 / 12.94 | 406 / 357 | 10.31x / 9.29x |
| Last five years | 69 | 64 | 13.85 / 12.85 | 111 / 100 | 9.54x / 8.47x |

The recent candidate adds 10 dates absent from baseline and removes 15 baseline dates, leaving 54 common dates. It can reduce original QLD switching while holding a 1x raw target. Counts are not guaranteed to fall every year: 2025 has 17→13 rebalances, while 2026 through September 25 has 13→14.

Applying the +15% cap **directly to confirmed targets without confirming the cap** instead raises recent rebalances **69→100**, annual turnover **9.54x→15.69x**, and gives recent CAGR/drawdown **18.17%/-21.02%**. This variant was not adopted.

## Sensitivity and limits

- At doubled 10bp costs, adopted-rule since-2010/recent CAGR is **18.56%/18.77%**, versus equally costed baseline **18.18%/17.36%**.
- With one additional execution day applied to both, adopted-rule since-2010/recent CAGR is **19.32%/20.57%**, versus baseline **19.16%/20.14%**. The recent drawdown advantage disappears: both have approximately **-19.92%**. Timing materially affects results.
- In 2011–2014 the adopted rule lowers CAGR **20.49%→19.39%**. It does not dominate in every era.
- There are 1,580 price-condition days in 97 consecutive intervals over the research history, irrespective of leverage eligibility. These are not 97 actual trading signals. In 2020-05-29 through 2020-10-29, extension stays above 15% for 108 trading days; extension can persist through sustained trends.
- No short-interest/order-flow data were used. Benefits cannot be attributed to short sellers. Price can also consolidate while its moving average catches up.
- Thresholds were compared on already-researched history. Pre-2006 QLD is synthetic; slippage, taxes and liquidity are not fully modeled. Historical results do not establish future returns.

## Implementation validation

`indicators.cap_overextension()` supplies the same scalar/vector cap to backtest, daily check, optimization and ablation. Regression tests use a deterministic synthetic trend/bear/recovery history and mock data access, so CI does not need market downloads. Full local cached-history checks also matched raw and confirmed targets across all four entrypoints, the research definition, and baseline-disabled execution.

Run `python -m unittest discover -s tests -p 'test_*.py'` to verify strict thresholds, post-volatility placement, unchanged lower targets, invalid-SMA warm-up, confirmation in both directions, unchanged decision tiers, next-open alignment and cross-entrypoint parity. Run `python 2_backtest.py` then `python 3_generate_report.py` with a prepared price cache for the production report. The Cloudflare build independently downloads fresh prices and validates the report dates.

Research price-cache SHA-256: `7f053199ab5ba1a10606ecbe0d65ba6028ebf336e7c608807efd3a0ec8a6092d`.
