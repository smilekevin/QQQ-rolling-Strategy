# Momentum Prediction and Higher-Return Research

Study date: 2026-10-13. Production strategy: V1.6.1. Price cutoff: 2026-09-25.

## Assessment

The user accepts greater risk, so this study examines both returns and drawdown tradeoffs. A modest increase in ordinary bullish C-tier exposure is the most promising candidate for further validation, followed by higher B-tier exposure. Evidence is insufficient to anticipate the next reversal from momentum acceleration and increase exposure early.

These are exploratory historical findings, not a production upgrade decision. Production, daily-check and Pine rules remain unchanged.

## Can momentum predict gains and declines?

Momentum indicators convert realized price changes into trend, strength and speed. They may contain conditional predictive information, but slowing gains do not imply an imminent decline. Shrinking MACD histograms, falling RSI and divergences need tests against subsequent executable returns; appearing before a chart’s peak is not proof.

Academic time-series momentum supports medium-term trend persistence. Moskowitz, Ooi and Pedersen studied 58 futures/forward contracts, mainly monthly-to-yearly trends. This does not establish next-day QQQ reversal prediction or a particular MACD rule’s edge. [Paper overview](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum)

Use fixed ridge regression with annual walk-forward training. From 2010, each test year uses only prior observations with fully observable labels; exclude training labels whose return windows enter the test year. Normalize on training data only; fix regularization at 10 without parameter search.

- Price controls: 5/20-day returns, 63-day drawdown, 20-day volatility and macro regime.
- Current indicators: add price-normalized MACD line/histogram, RSI14, Supertrend direction and distance from SMA250.
- Momentum acceleration: add five-day MACD histogram change/current price and five-day RSI change.
- Longer momentum: add 63/126/252-day price gains to current indicators.

Targets are QQQ returns from buying at the T+1 open to selling at the T+h close, with 5bp each way, excluding the signal-close-to-next-open gap. The table shows relative mean-squared-prediction-error improvement after adding each feature group: positive means better, negative worse.

| Horizon | Current indicators vs price controls | Acceleration vs current indicators | Longer momentum vs current indicators |
|---|---:|---:|---:|
| 1 day | -0.14% | +0.03% | +0.01% |
| 5 days | -0.67% | -0.49% | -0.19% |
| 20 days | +0.29% | -0.12% | -2.22% |
| 63 days | +3.87% | +0.02% | -5.94% |

For current indicators and acceleration, rough 95% intervals from resampling whole years 4000 times all include zero. Prediction errors use daily observations with overlapping longer windows. Year resampling preserves within-year dependence but not all cross-year dependence. Longer momentum worsens this model’s 20/63-day errors. These results show no stable extra predictive advantage in this fixed linear model, but do not rule out nonlinear conditions or different horizons, nor refute classic cross-asset time-series momentum.

QQQ net returns are positive in 66.45% of the 20-day prediction windows; the current-indicator model’s directional accuracy is 61.80%. Accuracy above 50% alone is insufficient: compare with always predicting gains in the same period. Mean-squared error, directional accuracy and tail-risk control are different objectives and do not directly determine allocation returns.

A descriptive non-overlapping check uses one fixed window every 20 trading days. Bullish regimes with momentum ≥3 have 173 windows averaging +0.48%; 0–2 points have 84 windows averaging +2.35%. At 63 days, averages are +3.52% and +2.23%. Short-term repair and medium-term trend continuation may coexist, but small samples and unmatched regimes/volatility do not justify reversing the score’s trading direction.

Rerunning `ablation.py` with updated data gives full-period CAGR/drawdown approximately 15.2%/-26.9%; no MACD 15.4%/-27.6%; no RSI 13.4%/-26.9%; no Supertrend 13.2%/-26.9%. Removing RSI also removes the floor. Ablation changes the full state/trade path; differences are not each indicator’s independent predictive power.

## Return comparisons when accepting more risk

All candidates retain macro state, E/F priority, RSI floor, volatility scaling, three-day confirmation, 0.05 increments, 0.15 deadband, shared next-open execution and 5bp per-side costs. Only base exposures change:

- B=2x: every current B tier changes from 1.5x to 2x. This is not directly equivalent to the earlier strategy’s 2x mechanism.
- C=1.25x: B remains 1.5x; raise C from 1x to 1.25x only when existing `lever_ok` holds; other C rules stay unchanged.
- Joint B/C increase: B=1.75x, leverage-eligible C=1.25x. A combined comparison, not attributable to one isolated change.
- R=1x: bearish reversal-recovery base increases from 0.75x to 1x, retaining volatility scaling and floor protection, without QLD.

Cells are CAGR / maximum drawdown. Subperiods preserve full-history state/holdings and include first-day returns from the prior trading close. Closing drawdown includes initial capital. Results may differ slightly from older first-day normalization or fresh-entry methods.

| Candidate | Full period (since 1999) | Actual QLD (since 2006) | Since 2010 | Last five years |
|---|---:|---:|---:|---:|
| V1.6.1 | 15.21% / -26.91% | 17.65% / -26.91% | 18.79% / -26.91% | 17.92% / -21.84% |
| B=2x | 16.15% / -31.25% | 18.90% / -31.25% | 20.67% / -31.25% | 18.16% / -24.90% |
| Leverage-eligible C=1.25x only | 16.23% / -32.55% | 18.50% / -32.55% | 19.67% / -32.55% | 19.53% / -22.58% |
| B=1.75x / eligible C=1.25x | 16.84% / -36.24% | 19.19% / -36.24% | 20.56% / -36.24% | 19.85% / -24.12% |
| R=1x | 15.32% / -26.91% | 17.87% / -26.91% | 19.01% / -26.91% | 18.04% / -23.49% |
| QQQ buy and hold | 10.90% / -82.96% | 16.65% / -53.40% | 19.20% / -35.12% | 15.56% / -35.12% |

The five-year start is the cutoff minus five years, 2021-09-25; the first valid trading date is 2021-09-27. From 1999 to QLD listing, existing synthetic QLD remains included and is not actual leveraged-ETF history.

C alone is a milder research candidate: since 2010, CAGR rises 0.88 percentage points and drawdown deepens 5.64 points. Narrowing the B/C exposure gap reduces full-period annualized one-way turnover from 8.41x to 5.64x. Return changes reflect risk-taking and altered trades, not more accurate prediction.

B=2x increases full-period turnover to 15.36x; recent CAGR rises only 0.24 points while drawdown deepens 3.06 points. R=1x also has small gains and worse recent drawdown, so is not a priority.

## Costs, execution and different eras

Cells remain CAGR / maximum drawdown, since 2010.

| Candidate | Normal execution, 5bp | Normal execution, 10bp | One extra execution day, 5bp |
|---|---:|---:|---:|
| V1.6.1 | 18.79% / -26.91% | 18.18% / -26.95% | 19.16% / -28.63% |
| B=2x | 20.67% / -31.25% | 19.53% / -31.33% | 20.94% / -35.04% |
| C=1.25x | 19.67% / -32.55% | 19.27% / -32.56% | 20.09% / -30.43% |
| B=1.75x / C=1.25x | 20.56% / -36.24% | 19.89% / -36.27% | 20.78% / -33.63% |
| R=1x | 19.01% / -26.91% | 18.39% / -26.95% | 19.44% / -28.63% |

C retains a gain with doubled costs, but adding one execution day to all candidates in the last five years makes baseline CAGR 20.14% and C 19.96%, erasing relative gains. Delays sometimes improving backtests do not justify intentional delay; recent rankings are sensitive to entry/exit timing.

| Period | Baseline CAGR / drawdown | C=1.25x CAGR / drawdown |
|---|---:|---:|
| 2011–2014 | 20.49% / -19.63% | 21.22% / -20.59% |
| 2015–2018 | 9.54% / -17.35% | 10.45% / -18.32% |
| 2019–2022 | 15.90% / -26.91% | 15.76% / -32.55% |
| 2023 to cutoff | 29.12% / -19.19% | 31.81% / -20.17% |

2019–2022 shows that increasing C is not worthwhile in every era. Higher final cumulative returns do not justify ignoring failure periods.

## Other return-improvement paths and next steps

1. **Moderately increase C:** freeze the single candidate above, assess willingness to tolerate historical closing drawdowns around 33% and worse future scenarios, and record forward performance without more table-driven tuning.
2. **Separate risk reductions from trend confirmation:** investigate faster cuts under sudden risk and how to restore exposure. Broadly shortening reduction confirmation previously performed poorly; faster is not automatically better. No new risk-channel rule is introduced here.
3. **Reduce turnover and actual trading costs:** current full-period turnover is 8.41x/year. Each 1bp reduction in one-way costs saves roughly 0.084 percentage points/year on nominal traded amounts; actual results also depend on slippage, trades and taxes.
4. **Add complementary return sources:** compare gold/managed futures with equal cash allocations. Earlier cross-asset work supports diversification value, but not guaranteed higher long-term returns; gold’s recent strength and short fund histories can bias conclusions.
5. **Keep momentum improvements as research:** first establish incremental executable information beyond existing states, then test allocation integration. Shrinking histograms and divergences are not standalone early-exit or leverage triggers for now.

Volatility management and turning-point prediction can be assessed separately. Moreira and Muir provide evidence for reducing risk during high volatility, but their return definitions and portfolios differ from this project; their reported gains cannot be transplanted directly. [Research paper](https://www.nber.org/papers/w22208)

All history has informed strategy development; chronological training does not make this an untouched final out-of-sample test. Historical maximum drawdown is not a future risk cap. Personal taxes, extreme intraday losses and all real opening slippage are excluded.

## Reproduction and validation

Run `.venv/bin/python momentum_research.py` without downloading prices. Default output is `/private/tmp/qqq_momentum_20261013`, including full results JSON, daily predictions/features and candidate equity/exposure/turnover CSVs. Temporary files are not a durable archive; identical inputs can rebuild them.

The study reuses baseline loading, confirmation, forward returns and statistics from `breadth_research.py`. Baseline loading stops before `2_backtest.py` writes reports, without overwriting `results.json`. Portfolios call `execution.run_next_open()`.

Verified: exact baseline target weights/equity; future windows start at the next open; incomplete tail windows excluded; indicator prefixes unchanged by later prices; no NDX proxy returns; candidate weights sum to 1 with target exposure in 0–2x. No within-tier rebalancing; actual weights may drift.

Price-file SHA256: `7f053199ab5ba1a10606ecbe0d65ba6028ebf336e7c608807efd3a0ec8a6092d`.
