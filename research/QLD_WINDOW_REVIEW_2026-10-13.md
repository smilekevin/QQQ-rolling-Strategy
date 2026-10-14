# Shorter QLD Exposure Window Study

Study date: 2026-10-13. Strategy: V1.6.1. Price cutoff: 2026-09-25.

## Assessment

This study aims to shorten QLD holding windows, reduce drawdowns and preserve as much return as possible, without increasing leverage. No single rule has yet shown materially lower drawdown with almost unchanged returns across both eras and the last five years.

The clearest tradeoff candidate is: **hold QLD for at most 20 trading days within an original continuous leverage window; exit early when QQQ falls 5% from its running closing peak within that window; replace QLD with QQQ until the original confirmed target returns to ≤1x, allowing a new window.**

- Last five years: CAGR 17.92%→17.17%, maximum drawdown −21.84%→−19.60%, QLD holding-day share 44.1%→23.9%.
- Since 2010: CAGR 18.79%→17.77%, maximum drawdown −26.91%→−24.87%.
- With doubled costs or one extra execution day for every strategy, the recent direction of lower returns and shallower drawdown persists.
- This exploratory combination followed observation of individual rules, not preregistered independent validation. No further search for optimal days or stops was performed.

If giving up about 0.75–1.0 percentage points/year to reduce historical maximum drawdown by about 2 points is acceptable, the candidate merits forward observation. Evidence is insufficient for retaining all returns. Production rules are unchanged.

## Why not exit only by holding days?

QLD targets twice the Nasdaq-100’s daily return. Multiday returns depend on path, volatility, fees and financing. Longer holding increases compounding divergence but does not imply inevitable losses beyond a particular day count; steady low-volatility gains differ from volatile sideways markets. [ProShares description](https://www.proshares.com/our-etfs/leveraged-and-inverse/qld)

Use only completed original-strategy windows that began after actual QLD launched. QQQ/QLD window returns run from the actual entry open to exit open using adjusted prices. This descriptive table does not separately deduct trading costs; actual prices already reflect fund fees.

| Final window length, known afterward | Windows | Average QQQ return | Average QLD return | QLD positive-return share |
|---|---:|---:|---:|---:|
| 1–20 trading days | 37 | -2.13% | -4.37% | 8.1% |
| 21–60 trading days | 38 | +3.65% | +6.75% | 71.1% |
| Over 60 trading days | 9 | +11.02% | +21.79% | 100.0% |

Most short windows lose because trend failure ended them; long windows survived rising markets. **Final duration is known only afterward. This table cannot predict a new window’s success, and long holding itself cannot be treated as the cause of gains.**

Before the 2020 crash, the original QLD window ran from the 2020-02-07 open to the 2020-02-27 open, only 13 trading days. QQQ returned about −7.97% and QLD −15.68%. A 20-day cap had not triggered and cannot protect rapid failure in a new window. A within-window drawdown exit may address it, while still absorbing gaps before the exit open.

## Main sources of recent drawdown

Baseline maximum drawdown is about −21.84%, from 2021-11-19 to 2022-12-20. Of 272 trading days between those dates, only 9 held QLD after opening rebalancing; old QLD holdings may still absorb the overnight return before exit. Capping original leveraged targets at 1x with no QLD still loses about 19.60% over those dates and has a last-five-year maximum drawdown around −19.60%.

QLD amplifies losses, but core equity exposure retains substantial risk. Shorter QLD windows can reduce some drawdown without removing QQQ’s own decline risk. No QLD is not a mathematical drawdown lower bound for all other possible filters.

## Common execution and candidate definitions

First reconstruct the original macro state, oversold latch, volatility scaling, three-day 0.05-increment confirmation and 0.15 deadband. Overlay QLD restrictions on **confirmed post-close targets**. Every original target ≤1x stays exactly unchanged. Restrictions reduce targets above 1x to 1x, retaining QQQ rather than exiting to cash. The 1.25x comparison caps confirmed targets; it is not equivalent to lowering base B to 1.25x before recalculating volatility scaling.

Signals are fixed at the close and filled at the next trading open using the shared engine: old holdings overnight/cash interest → opening rebalance/costs → new holdings intraday. No within-tier rebalancing; exposure drifts. Target caps are not intraday hard caps. Actual QLD prices already contain fund fees; do not charge them twice.

Predefined individual comparisons: no QLD, 1.25x target cap, 20/60-day caps, current-B filter, momentum score 4 only, EMA20/EMA50 price filters, 5-day annualized volatility ≤20%, and 5% within-window QQQ drawdown exit. 20 days approximates a trading month, 60 a quarter; the volatility reference keeps the existing 20%, without grid search.

- Current-B, score-4, EMA and volatility filters: remove QLD at the next open when the condition fails. Restoration requires 3 consecutive closes satisfying it and original confirmed targets still permitting leverage.
- 20/60-day caps: count from the original leverage window’s first opening QLD holding. At the limit, switch to QQQ at the next open; do not restart until the original confirmed target is ≤1x. Price-filter exits do not reset the clock.
- 5% drawdown exit: track QQQ’s closing peak from the signal close that starts the original leverage window; evaluate at the close and execute next open. Latch the exit until the original confirmed target is ≤1x. This is a QQQ price condition, not a 5% QLD loss or 5% portfolio drawdown.
- 20-day + 5% combination: take the lower target from both restrictions. This later exploratory combination leaves other parameters unchanged.

QLD holding-day share counts days with actual post-opening-rebalance net exposure above 1x, including 1.05x–1.5x, rather than only exactly 1.5x. Windows may be truncated by reporting-period boundaries.

## Full comparisons

Last five years: 2021-09-27 to 2026-09-25. Subperiods preserve full-history indicators, holdings and cost state. First-day returns use the previous trading close; daily closing drawdowns include period starting capital.

| Candidate | Since 2010: CAGR / drawdown | Last five years: CAGR / drawdown | Recent QLD holding-day share |
|---|---:|---:|---:|
| V1.6.1 baseline | 18.79% / -26.91% | 17.92% / -21.84% | 44.1% |
| No QLD | 15.96% / -22.44% | 15.95% / -19.60% | 0.0% |
| Confirmed target capped at 1.25x | 17.59% / -24.69% | 17.18% / -20.74% | 44.1% |
| Maximum 20 days per window | 17.61% / -26.91% | 17.17% / -19.60% | 23.9% |
| Maximum 60 days per window | 18.97% / -26.91% | 17.92% / -21.84% | 44.1% |
| Exit QLD immediately when current tier is not B | 17.54% / -24.87% | 17.49% / -21.59% | 37.8% |
| QLD only at momentum score 4 | 16.58% / -25.18% | 16.36% / -20.59% | 20.2% |
| Exit QLD below EMA20 | 17.18% / -24.87% | 17.67% / -20.51% | 35.5% |
| Exit QLD below EMA50 | 17.70% / -25.99% | 17.77% / -21.84% | 41.8% |
| Exit QLD above 20% five-day volatility | 17.93% / -24.85% | 17.09% / -20.24% | 33.9% |
| Exit QLD at 5% within-window QQQ drawdown | 18.77% / -24.87% | 17.66% / -21.84% | 43.4% |
| 20-day cap + 5% within-window QQQ drawdown exit | 17.77% / -24.87% | 17.17% / -19.60% | 23.9% |

### Longer-history reference

Cells are CAGR / maximum drawdown. Since-1999 results include pre-2006 synthetic QLD. Actual QLD starts 2006-06-22.

| Candidate | Full period (since 1999) | Actual QLD (since 2006) |
|---|---:|---:|
| V1.6.1 baseline | 15.21% / -26.91% | 17.65% / -26.91% |
| No QLD | 13.78% / -22.44% | 15.38% / -22.44% |
| Maximum 20 days per window | 14.99% / -26.91% | 16.77% / -26.91% |
| Exit QLD at 5% within-window QQQ drawdown | 15.16% / -25.31% | 17.64% / -25.31% |
| 20-day cap + 5% within-window QQQ drawdown exit | 15.10% / -24.87% | 16.90% / -24.87% |
| Exit QLD below EMA20 | 14.13% / -24.87% | 16.21% / -24.87% |

### Individual mechanisms and tradeoffs

- **20-day cap:** roughly halves recent QLD time, trading about 0.75 CAGR points for 2.24 drawdown points. Alone, it does not improve 2020 maximum drawdown. Since 2010, about 78% of overlapping rolling three-year windows have lower CAGR than baseline. This is descriptive; windows are not independent.
- **60-day cap:** changes no recent window because the baseline’s longest recent window is exactly 60 days. It affects earlier history; recent equality does not establish long-term ineffectiveness.
- **5% window drawdown exit:** preserves long-term returns reasonably, giving up about 0.02 CAGR points since 2010 and improving drawdown about 2.04 points. Recent maximum drawdown is unchanged, so it does not meet this study’s goal alone.
- **EMA20 filter:** small recent return sacrifice, but larger losses in the long actual-QLD period and 2011–2018, with more turnover. Do not select it solely from recent results.
- **Score 4 only:** substantially reduces QLD windows but sacrifices more return; stronger indicator agreement is not validated as better leverage eligibility.
- **Five-day volatility gate:** responds earlier to volatility but increases turnover and lowers recent returns. Faster response is not automatically an improvement.

## Costs and execution delays

Cells show recent CAGR / maximum drawdown. Apply one extra day to all baseline/candidate signals and compare with the equally delayed baseline, not the undelayed one.

| Candidate | 5bp cost | 10bp cost | One extra execution day, 5bp |
|---|---:|---:|---:|
| V1.6.1 baseline | 17.92% / -21.84% | 17.36% / -22.07% | 20.14% / -19.92% |
| 20-day cap + 5% within-window QQQ drawdown exit | 17.17% / -19.60% | 16.61% / -19.79% | 19.40% / -18.34% |
| Exit QLD at 5% within-window QQQ drawdown | 17.66% / -21.84% | 17.09% / -22.07% | 19.86% / -19.92% |
| Exit QLD below EMA20 | 17.67% / -20.51% | 16.85% / -20.74% | 20.61% / -18.32% |

Under normal execution, recent turnover for the 20-day+5% combination is about 9.66x/year versus baseline 9.54x, without a material increase. EMA20 is about 14.00x; increasing per-side costs from 5bp to 10bp expands its recent CAGR sacrifice from about 0.25 to 0.51 points.

Delays sometimes improve backtest returns, reflecting timing sensitivity rather than justifying intentional delay. With doubled costs and extra delay, the 20-day+5% combination remains a lower-return/shallower-drawdown tradeoff, not a free return improvement.

## Different eras

| Period | Baseline CAGR / drawdown | 20-day+5% CAGR / drawdown |
|---|---:|---:|
| 2007–2010 | 13.75% / -25.46% | 13.77% / -21.77% |
| 2011–2014 | 20.49% / -19.63% | 19.45% / -18.47% |
| 2015–2018 | 9.54% / -17.35% | 8.71% / -17.35% |
| 2019–2022 | 15.90% / -26.91% | 15.61% / -24.87% |
| 2023 to cutoff | 29.12% / -19.19% | 27.25% / -18.01% |

In 2015–2018, drawdown is unchanged while CAGR loses about 0.83 points; since 2023, about 1.87 points are sacrificed. These are real costs of less leverage participation, not obscured by a higher final Calmar.

## Next decision

Do not add the combination to production or retune the 20 days/5% to hindsight peaks. Freeze the 20-day+5% exit as a research candidate and record signals, QLD days, trading costs, returns and drawdowns on future data not used in development.

To reduce drawdowns of the recent type toward 15%, separately study core QQQ exposure, macro exits or portfolio risk budgets. Shorter QLD windows alone did not establish stable improvements of that size.

All history has participated in strategy research, and the combination followed single-rule results. These are not untouched final out-of-sample proofs. Historical maximum drawdown is not a future cap; personal taxes, all actual opening slippage and intraday drawdowns are excluded.

## Reproduction and validation

Run `.venv/bin/python qld_window_research.py` without new downloads. Output at `/private/tmp/qqq_qld_windows_20261013` includes candidate equity/exposure/turnover CSVs, full signal targets, baseline QLD windows and results JSON. The system may delete temporary files; identical inputs can rebuild them. Updating prices changes results.

Verified: exact baseline weights/equity; every original post-close target ≤1x unchanged; no candidate raises targets; nonnegative weights summing to 1; 20-day counting excludes NDX warm-up holdings; time caps, stop latches and three-day restoration are invariant on historical prefixes; shared next-open execution and actual trading-day boundaries.

Price SHA256: `7f053199ab5ba1a10606ecbe0d65ba6028ebf336e7c608807efd3a0ec8a6092d`. Dependency/script hashes are in results JSON. Production backtest, daily check, Pine and page data were not rewritten by this study.
