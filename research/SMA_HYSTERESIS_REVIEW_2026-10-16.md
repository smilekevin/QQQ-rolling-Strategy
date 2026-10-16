# SMA250 Hysteresis and Confirmation Study

Study date: 2026-10-16. Price cutoff: **2026-10-15**. Final user choice for the unmerged **V1.7.0** release: **15% activation / 10% release, fast overheat cuts, confirmed restoration**. This supersedes the initial stateless and fully confirmed candidates.

## Final rule

**Overextension cap (V1.7.0):** a close strictly above `SMA250 × 1.15` activates a restriction latch; release only at or below `SMA250 × 1.10`. Keep the previous state in between. Cap the volatility-scaled raw target at 1x without raising lower targets. The overheat reduction to at most 1x bypasses three-day confirmation by updating confirmation state itself; leverage restoration and all other target changes retain three identical rounded signatures. Apply the existing 0.05 rounding and 0.15x deadband, then execute at the next open. Release permits leverage under the original rules; it never forces 1.5x. B/C tiers and leverage eligibility are unchanged.

The fast cut updates the confirmation state itself. It is not a separate stateless overlay that could immediately resurrect an old leveraged target when the latch releases. A single upper crossing activates the latch; it is not three consecutive closes above 15%. The remaining deadband can retain small target differences, and weights drift between rebalances. This is not an absolute ceiling on actual holdings.

## Method

QQQ extension is adjusted signal close / trailing SMA250 − 1; the average updates daily. Use full-history indicators, latch, confirmation and holdings before slicing periods. QQQ trades begin 1999-03-11 with NDX indicator warm-up. QLD before June 2006 is synthetic. Existing holdings absorb overnight returns and cash interest, then rebalance at the next open with 5bp per side; new holdings earn intraday returns. Rebalance only when target allocation changes.

Research includes the first subperiod daily return against prior closing capital and includes starting capital in drawdown, annualized at 252 trading days. Production subperiods instead rebase at the first close: selected-rule recent CAGR is 18.93% research versus 18.78% production. Recent five years start 2021-10-15. Nonzero opening turnover days count as rebalances, including the first entry in full history; a QLD-to-QQQ switch is one rebalance, two security orders.

## Hysteresis search with all target changes confirmed

These candidates all use three-day confirmation, including overheat cuts. They are historical comparisons, not the final fast-cut rule.

| Activation / release | Full CAGR | Since-2010 CAGR | Recent CAGR | Recent drawdown | Full rebalances | Recent rebalances |
|---|---:|---:|---:|---:|---:|---:|
| 15% / 15% | 15.51% | 18.85% | 19.08% | -19.60% | 336 | 66 |
| 15% / 14% | 15.40% | 18.66% | 18.84% | -19.60% | 334 | 66 |
| 15% / 13% | 15.49% | 18.88% | 18.98% | -19.60% | 324 | 61 |
| 15% / 12% | 15.49% | 18.88% | 18.98% | -19.60% | 324 | 61 |
| 15% / 10% | 15.62% | 19.09% | 19.60% | -19.60% | 314 | 55 |

Follow-up release thresholds 8%, 9% and 11% were explored on the same history. A 9% release matches 10% recent CAGR (19.60%) and 55 trades but has weaker full-history CAGR (15.44% versus 15.62%). An 11% release gives 18.98% recent CAGR / 61 trades. At 8%, recent CAGR rises slightly to 19.64%, but drawdown worsens to −20.96% and full CAGR falls to 15.38%. These adaptive comparisons do not establish a broad plateau or independent validation.

## Confirmation comparison at fixed 15% / 10% thresholds

Fast cut: while latched, lower confirmation state to at most 1x on that signal close, without waiting three days. Do not accelerate restoration or other changes. The final allocation still passes the existing deadband and executes next open. All-confirmation-disabled means CONFIRM=1 throughout the strategy; it is a separate, broader experiment.

| Variant | Full CAGR / drawdown | Actual-QLD CAGR | Since-2010 CAGR | Recent CAGR / drawdown | Full rebalances | Recent rebalances |
|---|---:|---:|---:|---:|---:|---:|
| Three-day confirmation throughout | 15.62% / -22.44% | 18.19% | 19.09% | 19.60% / -19.60% | 314 | 55 |
| **Fast overheat cut (selected)** | 15.47% / -22.44% | 17.98% | 18.87% | 18.93% / -19.60% | 314 | 55 |
| All confirmation disabled | 13.99% / -27.16% | 16.65% | 17.67% | 18.87% / -21.79% | 622 | 97 |

The selected fast cut changes 42 full-history signal days relative to fully confirmed hysteresis. It lowers recent CAGR by about 0.67 percentage points without improving the measured recent or full maximum drawdown. Rebalance counts are equal, but execution dates and turnover differ. The user chose the faster protective execution after reviewing these results; it is not the highest-return candidate. Disabling all confirmation nearly doubles full rebalances (314→622), worsens full drawdown, and was not selected.

| Recent-five-year CAGR sensitivity | Three-day throughout | Fast cut (selected) | All confirmation disabled |
|---|---:|---:|---:|
| 10bp per side | 19.20% | 18.53% | 18.27% |
| One additional execution day, 5bp | 21.30% | 20.99% | 17.24% |
| One additional execution day, 10bp | 20.90% | 20.58% | 16.65% |

| Era CAGR | Three-day throughout | Fast cut (selected) | All confirmation disabled |
|---|---:|---:|---:|
| 2011–2014 | 20.24% | 20.19% | 17.14% |
| 2015–2018 | 10.80% | 10.72% | 6.82% |
| 2019–2022 | 15.56% | 15.28% | 17.51% |
| Since 2023 | 29.62% | 29.12% | 29.68% |

Lower release thresholds do not dominate every era: with full confirmation, 15%/10% gives 15.56% CAGR in 2019–2022 versus 16.26% for 15%/15%. Fast cuts lower that further to 15.28%. Extra-day execution changes results materially and is a sensitivity check, not a performance forecast.

## September–October 2026 opening operations

| Opening execution | Prior target | New target |
|---|---:|---:|
| 2026-09-01 | 1.15x | 1.50x |
| 2026-09-17 | 1.50x | 1.00x |
| 2026-09-23 | 1.00x | 1.50x |
| 2026-10-06 | 1.50x | 1.00x |

The fast overheat cut executes October 6 rather than October 8 under full confirmation. There is no October 13 restoration under 15%/10% hysteresis; confirmed and executed targets remain 1x through October 15. This does not imply leverage will never return later.

## Validation and limits

All four calculation entrypoints match raw and executed targets on the complete fresh cache. Production targets match the independent pre-implementation research filter exactly; equity metrics and the four opening dates match saved research results. Regression tests cover strict thresholds, buffer memory, invalid-SMA warm-up, fast cuts, fresh three-day restoration after even a one-day latch, lower protective targets, next-open alignment, unchanged tiers and four-entrypoint parity. Run `python -m unittest discover -s tests -p 'test_*.py'`; run `python 2_backtest.py` then `python 3_generate_report.py` with a prepared cache for production exports. Exploratory scripts and machine-readable results remain local under the research archive convention.

Thresholds and timing alternatives were compared adaptively on previously researched history and overlapping periods. This is not independent out-of-sample validation. No short-interest data were used; returns cannot be attributed to short sellers. A strong trend can remain far above its moving average. Opening slippage, taxes and liquidity costs are not fully modeled. Historical drawdown is not a risk limit.

Fresh-cache SHA-256: `f6f1c75bbd585084e97ea1bd7605d21141b8e9b33ca7869fa229cbd22b5e1c8d`.
