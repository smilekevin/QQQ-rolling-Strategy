# SPY / SSO strategy research — 2026-11-05

Data cutoff: **2026-11-04**, the latest eligible completed NYSE session at the time
of the run. The independent implementation is in [`spy_strategy/`](../spy_strategy/README.md).
The original QQQ rules and deployment pipeline are unchanged.

## Outcome

The selected historical candidate retains a 75% SPY core and adds exposure in a
favorable SMA250 regime, up to a 1.5x target using SPY and SSO. It beats SPY buy and
hold in the full sample, in the real-SSO segment, and in the retrospective 2019+
test. It does **not** dominate SPY: recent maximum drawdown is deeper, several
calendar years lose to SPY, and much of the return advantage requires leverage.
This is an exploratory candidate, not established predictive alpha.

| Period | Strategy CAGR | SPY CAGR | Difference | Strategy max drawdown | SPY max drawdown |
|---|---:|---:|---:|---:|---:|
| full (1995-01-03–2026-11-04) | 13.90% | 11.18% | +2.72pp | -47.81% | -55.19% |
| train (1995-01-03–2009-12-31) | 11.01% | 7.95% | +3.06pp | -47.81% | -55.19% |
| validation (2010-01-04–2018-12-31) | 14.70% | 11.64% | +3.07pp | -24.71% | -19.35% |
| holdout (2019-01-02–2026-11-04) | 18.71% | 17.10% | +1.61pp | -36.79% | -33.72% |
| actual_sso (2006-06-22–2026-11-04) | 13.61% | 11.34% | +2.27pp | -47.81% | -55.19% |
| since_2010 (2010-01-04–2026-11-04) | 16.55% | 14.14% | +2.40pp | -36.79% | -33.72% |
| since_2020 (2020-01-02–2026-11-04) | 16.33% | 15.16% | +1.17pp | -36.79% | -33.72% |

All figures include 5bp per side and ETF distributions. Benchmark purchases pay
the same initial transaction cost. CAGR uses 252 trading days per year. Subperiods
include their first daily return against previous closing capital and inherit
existing positions; they do not reset portfolio weights. Neither portfolio pays
taxes in this simulation.

## Exact selected rules

`spy_strategy/selected.json` is the frozen parameter source for this variant.

1. Use SPY adjusted OHLC from 1993 for warm-up; execute returns from **1995-01-03**
   for every model and benchmark. No pre-inception index proxy is required.
2. Keep a **0.75x unleveraged SPY core**. Bearish states do not go to cash.
3. Track SMA250 with a stateful gate: exit bullish below the average; re-enter
   bullish only strictly above `SMA250 * 1.01` after an exit.
4. In a bullish regime, base exposure is 1.5x if SMA250 is rising relative to 20
   sessions earlier and 20-day realized volatility is below 35%; otherwise 1x.
   A bearish regime's base exposure is 0.75x.
5. Scale the portion above the core only:
   `raw = 0.75 + (base - 0.75) * min(1, 20% / realized_volatility)`.
   This keeps meaningful SPY participation during fast recoveries but also keeps
   meaningful SPY downside during bear markets. The core is a floor on targets,
   not a daily guarantee on the drifted SPY weight.
6. Preserve the shared **15% activation / 10% release** SMA overextension latch
   and 1x cap. Apply the existing fast overheat cut to confirmation state.
7. Round to 0.05x, use three consecutive identical signatures for ordinary
   changes, and a 0.15x deadband. **Ordinary bearish cuts still wait for
   confirmation**; only the overheat cut has the fast path.
8. Signal at T's close and rebalance at the next session's open, only when the
   target changes. Let holdings drift otherwise. At 1.5x, hold 50% SPY and 50%
   SSO; at 0.75x, hold 75% SPY and 25% cash. No additional account borrowing is
   assumed.

MACD, RSI, Supertrend and the bearish RSI latch are **not allocation criteria**
for the selected core/trend model. They remain in the multi-indicator comparator;
RSI in the latest-data export is informational. This is a simpler adaptation of
the allocation/risk framework, rather than a forced copy of every QQQ indicator.

A lower beta does not require multiplying every QQQ threshold by that beta.
Using common **1999–2009 training data only**, SPY's beta relative to QQQ is
**0.519** and its realized volatility ratio is **0.643**.
The coarse comparison included 12%, 16%, 20% and 24% volatility targets. The final
model retains a 20% target **only above its core**; its effect is therefore quite
different from scaling the QQQ allocation as a whole. The retained SMA250 and
15%/10% thresholds were outcomes of this comparison, not a claim that the assets
have the same beta.

## Selection and adaptive-research disclosure

- Training: **1995–2009**. Validation/development: **2010–2018**. Chronological
  historical test: **2019–2026-11-04**. Signal/indicator construction and parameter
  scoring inside selection receive data no later than 2018-12-31. Tests verify
  that changing later prices cannot change the selected parameters.
- The first grid contained **144** configurations: multi-indicator versus
  trend-only, SMA150/200/250, 12%/16%/20%/24% volatility target, no cap versus
  10%/7.5% versus 15%/10% cap, and one- versus three-session confirmation.
- A provisional direct adaptation and the initial selected trend strategy were
  inspected on recent history. The latter has full CAGR **12.78%** versus SPY
  **11.18%**, but test CAGR **15.12%** versus **17.10%**, and failed the local
  robustness gate. It is retained as a failed return-oriented alternative.
- The core/trend family was then added, using SMA150/200/250, 16%/20%/24% targets,
  0.5x/0.75x/1x cores, cap on/off and one/three-session confirmation: **108** extra
  configurations, **252 unique configurations** in total. This structural
  expansion was informed by the initial diagnostics. **The test history is not
  an untouched independent sample.** An earlier data-only chronological split
  does not erase this adaptive design choice or the original QQQ research.
- The first defensive development budget capped drawdown at 35%, which was an
  analyst assumption, not a user requirement. Extending the grid under that
  budget still rejected the higher-core models. The return-oriented comparison
  then used **SPY's development maximum drawdown of 55.19%** as the budget rather
  than silently implying the user required a 35% limit. This is a disclosed risk
  tradeoff, not an improvement under the original defensive constraint. Three
  development-selection passes used the same cached prices under these two
  budgets; 252 refers to unique configurations, not all repeated simulations.
- Eligibility requires positive excess CAGR in both train and validation and
  drawdown within the declared budget. The score is
  `min(train_excess, validation_excess) + 0.25 * mean(excesses)
  - 0.05 * max(0, worst_drawdown_magnitude - 0.25)`.
  Prefer median immediate-neighborhood score, with at least 70% qualifying local
  configurations; break ties on the direct score, then simpler family/order.
  Neighbors change one grid step of SMA, volatility, cap or core within a fixed
  family and confirmation setting. The selected neighborhood includes the center.
- **6 of 7** local configurations qualify under the return-oriented budget. The
  exact parameters were persisted before the final evaluation of this phase.
  No recent-period winner was substituted after seeing that final evaluation.
  This stability is useful historical evidence, not a multiple-testing-adjusted
  statistical guarantee or prospective verification.

## Leverage, cost and delay controls

| Variant | Full CAGR | Full max drawdown | 2019+ CAGR | 2019+ max drawdown |
|---|---:|---:|---:|---:|
| strategy | 13.90% | -47.81% | 18.71% | -36.79% |
| spy | 11.18% | -55.19% | 17.10% | -33.72% |
| unleveraged_rule | 11.07% | -43.90% | 15.84% | -29.55% |
| double_cost | 13.75% | -47.89% | 18.53% | -36.82% |
| extra_day_delay | 13.89% | -47.86% | 17.28% | -41.27% |
| static_spy_sso | 13.46% | -76.13% | 23.28% | -50.84% |
| qqq_parameters_on_spy | 11.70% | -33.16% | 12.57% | -33.16% |

The unleveraged form does not beat SPY. Do not attribute the whole advantage to
indicator timing. The buy-once 50/50 SPY/SSO benchmark beats the candidate recently
but has materially larger drawdowns; it is a drifting two-fund holding, not a
constant daily 1.5x benchmark. Doubling transaction costs preserves this sample's
advantage. One extra session of execution delay leaves only about **0.18pp** of
2019+ CAGR advantage and increases that period's drawdown to **41.27%**. Execution
sensitivity is a material limitation.

Observed full-sample opening exposure averages **1.24x**, with a maximum of
**1.57x** despite the 1.5x target limit, due to permitted position drift.
There are about **3.9** opening rebalances per year and **2.77x
one-way annual turnover. Realized daily-return beta to SPY is about **1.00**;
this ex-post statistic is not proof of predictive alpha.

The candidate's deepest full-sample drawdown occurs on **2009-03-09**. Recent
annual underperformance includes **2020 (13.67% versus 18.33%)**, **2022
(-21.54% versus -18.18%)**, **2023 (26.09% versus 26.18%)**, and **2025
(16.89% versus 17.72%)**. It does not beat SPY every year.

## Data and reproducibility

Yahoo Finance/yfinance adjusted SPY and SSO OHLC includes distributions and
actual ETF expenses. The NYSE calendar excludes partial current sessions and
requires one hour after the exchange's actual close, including early closes.
Missing post-inception SSO bars or stale ETF cutoffs fail rather than being filled.
Cash funding uses the previous available IRX observation, with no future backfill.

SSO listed on 2006-06-21; complete real overnight/intraday segments start
**2006-06-22**. Before that boundary, synthetic SSO daily return is
`2 * SPY_return - (0.95% + prior_IRX_yield) / 252`. Overnight is twice SPY's
actual overnight return and intraday is inferred to compound exactly to the daily
synthetic return. This uses an explicit fee assumption and a Treasury financing
proxy, without claiming that this ETF could have been traded before inception.
Actual SSO is never replaced by synthetic returns to bridge later missing bars.
The real-SSO-period comparison supports the historical result without relying on
pre-inception leverage, though holdings and signals carry across that boundary.

The shared execution engine assigns overnight returns to old holdings, then
costs/rebalancing at the open, then intraday returns to new holdings. Future
closing prices cannot determine that morning's trade. No source modifications or
parameter changes were made to the original QQQ strategy.

```bash
python -m spy_strategy backtest --refresh --as-of 2026-11-04
python -m spy_strategy research --phase initial --as-of 2026-11-04
python -m spy_strategy research --phase extended --as-of 2026-11-04
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/worker.test.mjs
```

The frozen parameter file is `spy_strategy/selected.json`. `research` writes a
separate selection under ignored `spy_strategy/output/`, without adopting it as
live configuration. The standalone bilingual HTML embeds the current run's data.
The [compact snapshot](./SPY_STRATEGY_SNAPSHOT_2026-11-05.json) preserves metrics,
selection, risk, provenance and limitations. Ignored raw CSVs preserve source-file
and actually-used-data SHA-256 hashes separately. Yahoo historical adjustments can
change after a refresh; identical cutoffs alone do not guarantee identical data.

## Remaining limits

Taxes, time-varying spreads, actual financing quotes before SSO, execution
capacity and live fills are not modeled. Neither robust neighbors nor a
chronological split adjusts for all the research choices made on familiar market
history. Forward performance can underperform SPY and drawdowns can exceed this
sample. SSO resets leverage daily and carries financing cost and volatility drag.
This candidate is suitable for further paper observation, not an assurance that
the user's future return objective has been achieved.
