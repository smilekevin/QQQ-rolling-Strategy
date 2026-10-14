# S5FI Market Breadth and QQQ Rebound Study

Study date: 2026-09-11. Strategy: V1.6.1.

## Conclusion

Recovering S5FI from low levels has an interesting conditional relationship with QQQ gains over roughly the next month, but this study did not validate a trading change that consistently improves the existing strategy. Five-day results are weak; favorable 20-day event statistics do not guarantee incremental returns after integration into allocation rules.

The study directly uses TradingView `INDEX:S5FI` history rather than rebuilding history from today’s S&P constituents. S5FI is the percentage of S&P 500 constituents above their own 50-day averages: 20 means 20%, not 20 stocks. It measures S&P participation, distinct from QQQ’s Nasdaq-100 universe.

## Data and execution

- Source: [TradingView INDEX:S5FI](https://www.tradingview.com/symbols/INDEX-S5FI/); public chart metadata identifies Barchart as provider.
- Downloaded 4977 daily bars from 2006-12-29 through 2026-09-10. Values stay within 0–100, dates are unique, and no strategy trading days are missing in the study period.
- QQQ uses project prices; SPY uses adjusted Yahoo Finance opening/closing prices. The common study cutoff is 2026-07-30, starting 2007-01-03. Later breadth data never predicts earlier returns.
- Breadth bars are labeled with the trading day’s New York 09:30 open; that day’s final close is the post-close signal. Provider revisions and final release timing were not independently audited, so breadth entries were also tested with one extra day of delay.
- Event returns: signal at the T close, buy at the T+1 open, sell at the T+5/T+10/T+20 close, with 5bp each way. Excludes gains on the signal day or before the next executable open.
- Within each signal group, events are at least 20 trading days apart to avoid counting the same holding window twice. Different signal groups may cover the same market periods and are not independent experiments.
- Benchmark windows start every 20 trading days on fixed dates, including ordinary and extreme markets. This is neither random sampling nor a strictly matched causal control.
- No independent constituent-level audit establishes point-in-time membership or provider revisions. Using provider history avoids the obvious bias of reconstructing from current constituents, but is not a complete point-in-time audit.

## Fixed signal definitions

| Signal | Rule observable after the close |
|---|---|
| Breadth enters oversold territory | S5FI falls below 20 from at least 20 the prior day |
| Recovery through 30 | Previous 10 trading days’ minimum S5FI ≤20; today crosses above 30 from ≤30 |
| Strong recovery through 50 | Previous 10 trading days’ minimum S5FI ≤20; today crosses above 50 from ≤50 |
| Price-recovery control | QQQ crosses above its 5-day average from at or below it |
| QQQ pullback context | QQQ is at least 5% below the highest close over the previous 63 days |

30 and 50 were predefined simple thresholds, not optimized values. Recovery through 50 is not the classic Zweig Breadth Thrust, which uses a different advancing-issue definition.

## Event statistics

Cells show average net QQQ returns, with positive-return share in parentheses. Returns include the 10bp round trip.

| Signal | Events | Next 5 days | Next 10 days | Next 20 days |
|---|---:|---:|---:|---:|
| Benchmark window every 20 trading days | 246 | +0.33% (61.0%) | +0.47% (61.8%) | +1.18% (66.3%) |
| Breadth falls below 20 | 35 | -0.21% (45.7%) | +0.31% (42.9%) | +2.86% (71.4%) |
| Recovery through 30 | 30 | -0.29% (46.7%) | +0.72% (66.7%) | +3.19% (76.7%) |
| Strong recovery through 50 | 23 | -0.68% (39.1%) | +1.90% (78.3%) | +3.29% (73.9%) |
| Price crosses 5-day average after ≥5% QQQ pullback | 72 | -0.11% (48.6%) | +0.12% (58.3%) | +1.55% (63.9%) |

A closer pullback-context comparison: recovery through 30 with QQQ at least 5% below its peak produced 24 events, average 20-day return +3.29% and win rate 75.0%; 107 deduplicated windows with only the ≥5% QQQ pullback produced +1.55% and 60.7%. This supports further conditional-signal research, but risks and event dates are not fully matched, so the difference is not causal excess return.

Resampling event years as whole blocks 2000 times gives a rough 95% interval of +1.82% to +5.15% for recovery-through-30 average 20-day returns. This is not a significance test against the benchmark. The five-day mean’s interval crosses zero. Only 30 events are available; grouping by year does not remove all cross-year dependence.

For the same recovery-through-30 signal in SPY: average 20-day return +2.32%, win rate 70.0%; five-day -0.20%, win rate 43.3%. Neither QQQ nor SPY shows a reliable five-day buying edge.

QQQ 20-day recovery-through-30 results by era:

| Era | Events | Average net return | Positive-return share |
|---|---:|---:|---:|
| 2007-2012 | 14 | +2.48% | 71.4% |
| 2013-2019 | 7 | +3.59% | 85.7% |
| 2020-2026 | 9 | +3.97% | 77.8% |

Direction agrees across the three eras, but later samples are especially small. These remain exploratory historical checks.

## Correlation and incremental predictive information

- S5FI five-day change correlates about +0.704 with contemporaneous QQQ five-day returns: breadth and index gains often occur together.
- The same change correlates -0.029/+0.006/+0.008 with executable future 5/10/20-day returns, a weak linear relationship.
- Breadth level correlates about -0.099 with future 20-day returns. Low breadth has some rebound tendency, far from precise daily prediction.

To test beyond existing price information, use fixed annual walk-forward ridge regression. Controls are QQQ 5/20-day returns, 63-day drawdown, RSI14, 20-day volatility and macro regime; then add S5FI level and five-day change. From 2012, each year trains only on earlier data, excludes training labels crossing into the test year, normalizes with training means/deviations only, and fixes regularization at 10.

| Horizon | Test mean-squared-error change after adding breadth |
|---|---:|
| 5 days | Increase of 0.52% |
| 10 days | Increase of 0.83% |
| 20 days | Increase of 1.22% |

Year-resampled intervals all include zero, so breadth is not proven harmful. This simple model shows no stable incremental predictive improvement; it does not rule out nonlinear rare-event rules.

## Integration with the current strategy

Entry candidate: after a breadth or price event, with a ≥5% QQQ 63-day pullback and confirmed post-close strategy target below 0.30x, set a 0.30x exposure floor for 20 trading days from the next open, using only QQQ and no extra QLD. Do not extend the holding period. Higher original targets take priority. Restore original targets at the open after expiration; old holdings still absorb overnight returns. This floor bypasses the original three-day confirmation and is a separately researched execution-rule change.

Also test a breadth leverage gate: below S5FI 50, cap raw target exposure at 1x, then apply original three-day confirmation, deadband and next-open execution. It does not immediately liquidate drifted holdings.

All portfolios use the shared engine and 5bp per-side costs; production is unchanged. Main period: 2007-01-03 to 2026-07-30. Subperiods retain earlier holdings and include first-day returns; do not mix these results with prior first-close normalization or first-open fresh-entry figures.

| Rule | Full-period CAGR / maximum drawdown | Last-five-year CAGR / maximum drawdown |
|---|---:|---:|
| V1.6.1 baseline | 17.07% / -26.91% | 16.56% / -21.84% |
| 0.30x floor after breadth falls below 20 | 17.26% / -29.86% | 17.74% / -21.39% |
| 0.30x floor after recovery through 30 | 17.04% / -26.91% | 16.34% / -23.69% |
| Recovery through 30, one extra execution day | 17.07% / -26.91% | 16.40% / -23.34% |
| 0.30x floor after price recovery | 16.91% / -35.11% | 16.86% / -23.91% |
| Limit leverage below S5FI 50 | 16.38% / -26.91% | 15.67% / -21.06% |

High event win rates do not guarantee strategy gains. Of 30 distinct recovery-through-30 events, only 14 met the low-exposure condition and actually activated the floor. Returns also change after selecting the low-exposure subset. Existing R/D/F states already participate in some subsequent gains.

| Year | Original strategy | Floor after below-20 entry | Floor after recovery through 30 |
|---|---:|---:|---:|
| 2008 | -12.41% | -16.17% | -12.95% |
| 2011 | -7.68% | -7.79% | -7.54% |
| 2016 | -1.38% | +0.88% | -0.92% |
| 2020 | +27.05% | +27.15% | +27.11% |
| 2022 | -17.72% | -14.90% | -19.00% |
| 2025 | +7.75% | +9.57% | +8.45% |

At 10bp per-side costs, full-period CAGR is baseline 16.51%, below-20 floor 16.69%, recovery-through-30 floor 16.47%, and leverage gate 15.81%. There is no robust return/drawdown advantage supporting immediate adoption.

## Specific failure scenarios

- 2008-09-29: S5FI 8.89. Buying QQQ at the next open still loses about 24.02% after 20 trading days. Extremely low breadth can signal a continuing crisis, not a guaranteed bottom.
- 2022-05-17: S5FI crosses 30 to 31.28. Next-open QQQ entry earns about -6.31% over 20 trading days; worst closing loss versus entry is about -8.67%. The rebound fails; the floor candidate changes relative window equity by about -2.64% versus baseline.
- 2020-04-14: recovery through 30 precedes +6.44% QQQ 20-day returns, but the floor improves strategy window equity by only about 0.05%. A strong rebound does not imply the original strategy missed it.
- After the 2025-04-24 signal, QQQ’s 20-day net return is about +9.96%, but strategy annual return improves only from 7.75% to 8.45%, insufficient to establish effectiveness.

Relative window equity change is the change in candidate/baseline equity ratios across the event, not an additive return contribution. Strategy windows include the restoration trade at the next open after expiration, slightly differing from standalone events sold at the 20-day close.

## Next steps

Prefer S5FI as an observation of market participation and rebound durability. Below 20 means broad oversold conditions; recovery through 30 means repair is spreading; above 50 means most constituents are back above their 50-day average. None is a standalone trading instruction.

Evidence does not support raising leverage or adding any candidate to V1.6.1. Further research could apply identical rules to Nasdaq-100 breadth, with a predefined validation plan, to see whether it better matches QQQ. Do not retune thresholds after 2025 or one failed rebound to chase a better curve.

Event rules, allocation changes and ridge regression are research tools. History has already informed strategy development. Even chronological prediction training does not make the whole study an untouched final out-of-sample test.

## Reproduction and validation

- `breadth_research.py --download` downloads S5FI through a public guest-price connection and downloads SPY, then runs the study. Omit `--download` with existing data. Requires the project Python environment and yfinance, websockets, pandas and numpy.
- Default data directory: `/private/tmp/qqq_breadth_20260911`; override with `--data-dir`. Prices, individual events, predictions, candidate equity and results JSON are written there; daily data is not committed.
- Checked opening/closing offsets in forward returns, incomplete final windows, fixed non-renewing holding periods, prefix invariance to future data, weights summing to 1, original targets without events, and exact reconstruction of confirmation/deadband targets.
- Provider metadata is saved as `S5FI_metadata.json`; source checksums are in results JSON. Public-interface availability/history length may change, and redownloads may include revised provider history.
- S5FI input SHA256: `e64b2318278606f76c2a5134197c8665375c2f2c3d76c706998eee2efc858991`.
- QQQ strategy price SHA256: `43c1bb379086e57db7271fe3a3c2abc24e37fa5363d8968f2b9229ad3dd2aa21`.
