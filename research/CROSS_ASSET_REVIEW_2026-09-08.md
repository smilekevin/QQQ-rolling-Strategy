# Cross-Asset Allocation Review

Review date: 2026-09-08. Strategy: V1.6.1. Common market-data cutoff: 2026-07-30.

## Assessment

Gold’s strong last-five-year performance cannot be assumed for future returns. A 20% gold allocation improved both returns and drawdown recently, but since 2006 the tradeoff was lower returns for lower drawdown. During weak gold markets in 2012-2018, 20% gold produced worse returns and drawdown than the same allocation to cash.

To reduce dependence on further gold appreciation, compare these three research allocations first:

- 80% original strategy + 20% SGOV: the simplest lower-risk comparison, reducing strategy capital and investing external cash in an actual ultra-short Treasury ETF.
- 80% original strategy + 10% DBMF + 10% SGOV: no gold, with managed futures as a complementary return source; DBMF has a short live history and requires continued observation.
- 80% original strategy + 10% GLD + 10% SGOV: retain a smaller gold allocation while accepting possible underperformance versus cash when gold weakens.

These are research allocations, not optimal weights, and do not change production.

## Methodology

- Nominal USD returns using Yahoo Finance opening/closing prices adjusted for dividends and splits. Fund fees are already reflected in prices and are not deducted again. Personal taxes and currency-conversion costs are excluded.
- Long period: 2006-06-22 to 2026-07-30, excluding synthetic QLD. Last five years: 2021-07-30 to 2026-07-30.
- Each period starts anew in cash, buying at its first trading open. Indicators and confirmation state warm up on full history. Cash before that open earns interest under the existing IRX model.
- Strategy signals are fixed at the prior close and filled at the next open. Internal rebalancing occurs only when targets change; weights drift while held.
- Outer asset allocations rebalance at the first trading open of each month. Capital added to or removed from the strategy retains its internally drifted asset proportions unless a strategy transition also occurs.
- Equity/ETF trades cost 5bp per dollar traded. Simultaneous trades are netted; cash-balance changes alone incur no cost. Costs follow the existing engine’s approximation.
- Portfolio drawdown comes from the combined daily equity series, including initial capital, not weighted averages of individual drawdowns. Closing drawdowns do not describe the deepest intraday losses.
- Annualization uses 252 trading days. Results differ slightly from earlier slices of a long-held equity curve, mainly because of opening entry and first-day returns.
- The original strategy already earns interest on cash. SGOV is an additional external allocation; existing cash interest cannot be counted again as incremental income.
- DBMF has actual data only from 2019 and SGOV from 2020; no invented long history is spliced in.

## Individual assets

Each cell is CAGR / maximum drawdown for buy and hold. Initial trading costs affect very small drawdown figures for low-volatility assets such as SGOV.

| Asset | Role | Since 2006 | Last five years | Five-year total return |
|---|---|---:|---:|---:|
| QQQ | Nasdaq equity benchmark | 16.30% / -53.40% | 14.26% / -35.12% | +94.23% |
| GLD | Gold | 9.76% / -45.56% | 17.24% / -26.40% | +120.81% |
| SHY | 1-3-year US Treasuries | 1.99% / -5.71% | 1.78% / -5.71% | +9.18% |
| IEF | 7-10-year US Treasuries | 3.42% / -23.92% | -1.75% / -21.40% | -8.39% |
| TLT | US Treasuries over 20 years | 3.15% / -48.35% | -8.05% / -43.70% | -34.16% |
| DBC | Broad commodity futures | 2.09% / -76.36% | 11.55% / -27.34% | +72.36% |
| DBMF | Managed futures | Insufficient history | 8.26% / -20.39% | +48.49% |
| SGOV | 0-3-month US Treasuries | Insufficient history | 3.66% / -0.06% | +19.60% |

SGOV is for short-term cash management; yields vary with market rates. SHY, IEF and TLT have progressively longer durations and more interest-rate sensitivity. TLT is not a low-risk cash substitute. Futures roll effects also shape DBC’s long-term returns; recent performance is not a long-term allocation assumption.

## Fixed allocations

S denotes the original V1.6.1 strategy. Cells are CAGR / maximum drawdown; total returns are separate.

| Allocation | Since 2006 | Last five years | Five-year total return |
|---|---:|---:|---:|
| 100% S | 17.35% / -26.91% | 16.93% / -21.84% | +117.87% |
| 80% S + 20% cash model | 14.34% / -22.06% | 14.50% / -17.50% | +96.29% |
| 90% S + 10% GLD | 16.91% / -25.06% | 17.31% / -20.06% | +121.46% |
| 80% S + 20% GLD | 16.39% / -23.18% | 17.62% / -18.80% | +124.37% |
| 70% S + 30% GLD | 15.80% / -21.26% | 17.85% / -17.95% | +126.55% |
| 80% S + 20% SHY | 14.43% / -21.75% | 14.07% / -18.47% | +92.64% |
| 80% S + 20% IEF | 14.81% / -21.02% | 13.26% / -20.34% | +85.92% |
| 80% S + 20% TLT | 14.91% / -23.69% | 11.78% / -23.69% | +74.12% |
| 80% S + 20% DBC | 14.63% / -26.60% | 16.54% / -16.91% | +114.35% |
| 70% S + 20% GLD + 10% IEF | 15.05% / -20.16% | 15.69% / -18.36% | +106.63% |
| 70% S + 20% GLD + 10% SHY | 14.87% / -20.53% | 16.10% / -17.32% | +110.35% |
| 80% S + 20% SGOV | Insufficient history | 14.49% / -17.58% | +96.18% |
| 80% S + 20% DBMF | Insufficient history | 15.64% / -16.66% | +106.23% |
| 80% S + 10% GLD + 10% SGOV | Insufficient history | 16.06% / -18.00% | +109.95% |
| 80% S + 10% DBMF + 10% SGOV | Insufficient history | 15.07% / -16.06% | +101.23% |
| 70% S + 15% GLD + 15% DBMF | Insufficient history | 16.43% / -13.74% | +113.28% |

GLD’s gains are concentrated recently; five-year results do not establish 30% gold as optimal. DBMF portfolios are interesting in this period, but lack actual fund performance in 2008, and strong 2022 results may materially influence the assessment.

## When gold was weak

2012-2018 is a selected historical scenario: a hindsight stress check, not untouched out-of-sample validation.

| Allocation | CAGR | Maximum drawdown |
|---|---:|---:|
| GLD alone | -3.44% | -42.11% |
| Original strategy | 18.40% | -17.35% |
| 90% original strategy + 10% GLD | 16.28% | -15.71% |
| 80% original strategy + 20% GLD | 14.13% | -14.76% |
| 80% original strategy + 20% cash model | 14.83% | -13.90% |

At the same 80% strategy allocation, gold delivered lower returns and deeper drawdown than cash in this period. Diversification value does not justify a large allocation in every regime.

## Hypothetical lower-gold-return stress tests

Keep the actual five-year paths of the strategy and other assets. Subtract a constant from gold’s daily intraday log return to reach pre-trading-cost CAGR of 5%, 0% or -5%. Daily log-return volatility is unchanged: gold still moves, rather than becoming flat. Cash interest before the first opening purchase is included in calibration.

These are sensitivities on fixed historical paths, not five-year forecasts. Real return changes can also alter volatility and asset correlations, so the drawdowns are not future risk caps.

| Gold CAGR scenario | 90% S + 10% GLD: CAGR / drawdown | 80% S + 20% GLD: CAGR / drawdown | 80% S + 10% GLD + 10% SGOV: CAGR / drawdown |
|---|---:|---:|---:|
| Actual history about 17.24% | 17.31% / -20.06% | 17.62% / -18.80% | 16.06% / -18.00% |
| Hypothetical 5% | 16.03% / -21.02% | 15.06% / -20.30% | 14.79% / -18.90% |
| Hypothetical 0% | 15.47% / -21.43% | 13.95% / -21.06% | 14.23% / -19.32% |
| Hypothetical -5% | 14.88% / -21.86% | 12.80% / -21.92% | 13.65% / -19.77% |

The original strategy is 16.93% / -21.84% over the same period; 80% strategy + 20% cash is 14.50% / -17.50%. At hypothetical 0% gold CAGR, 20% gold loses to cash on both returns and maximum drawdown.

## 2022 check

| Allocation or asset | 2022 return |
|---|---:|
| QQQ | -32.58% |
| Original strategy | -17.72% |
| GLD | -0.77% |
| IEF | -15.16% |
| TLT | -31.23% |
| DBC | +19.34% |
| DBMF | +21.60% |
| SGOV | +1.58% |
| 80% S + 20% GLD | -14.38% |
| 80% S + 20% SGOV | -14.08% |
| 80% S + 20% DBMF | -10.60% |
| 80% S + 20% TLT | -20.47% |

Long Treasuries worsened losses in 2022, while managed futures and commodities buffered them. Asset names alone do not establish equity-hedging behavior.

## Data and validation

- yfinance reads public Yahoo Finance prices, with a cutoff matching the existing strategy price file. All 7 ETFs downloaded successfully; adjusted prices incorporate dividends.
- Reference prices: [GLD](https://finance.yahoo.com/quote/GLD/history/), [SHY](https://finance.yahoo.com/quote/SHY/history/), [IEF](https://finance.yahoo.com/quote/IEF/history/), [TLT](https://finance.yahoo.com/quote/TLT/history/), [DBC](https://finance.yahoo.com/quote/DBC/history/), [DBMF](https://finance.yahoo.com/quote/DBMF/history/), [SGOV](https://finance.yahoo.com/quote/SGOV/history/).
- Research script: `cross_asset_research.py`. Raw ETF prices and full JSON results default to `qqq_cross_asset_research` in the system temporary directory; daily prices are not committed.
- Verified: 100% strategy equity and turnover match the shared engine; no-cost flat markets preserve equity; cash compounding and ETF buy-and-hold reconstruction are correct; overnight/intraday returns reconstruct total daily returns.
- Gold scenarios reach their specified returns while retaining daily log-return volatility. Allocation weights were not grid-optimized.
- Original strategy price-file SHA256: `43c1bb379086e57db7271fe3a3c2abc24e37fa5363d8968f2b9229ad3dd2aa21`. Downloaded ETF hashes are recorded in results JSON.
