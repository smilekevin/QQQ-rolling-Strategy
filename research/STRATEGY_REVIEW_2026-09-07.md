# QQQ/QLD Strategy Reassessment

Date: 2026-09-07. Version assessed: V1.6.1. Data cutoff: 2026-07-30.

## Conclusion

The strategy deserves further work, but is more accurately described as a Nasdaq risk-management strategy than a proven alpha strategy that can consistently beat QQQ.

- The full-period advantage mainly comes from avoiding the 2000 dot-com collapse and the 2008 crisis. Strategy CAGR is about 15.0% and maximum drawdown about -26.9%, versus QQQ’s 10.6% and -83.0%.
- In the more representative period since 2010, strategy CAGR is about 18.3% versus QQQ’s 18.7%, with similar returns but a lower drawdown: -26.9% versus -35.1%.
- Over the last five years, strategy CAGR is about 16.8% versus QQQ’s 14.1%, and drawdown -21.8% versus -35.1%. This is encouraging, but the sample is short and does not establish long-term excess returns.
- After actual QLD launched, strategy CAGR is about 17.4% versus QLD’s 24.9%, but drawdown is -26.9% versus about -83.1%. The strategy buys substantially lower risk rather than capturing all QLD upside.

The next goal should be consistent executable accounting, reducing losses from confirmation delays, and selecting a small number of changes using strict chronological validation, rather than adding more indicators.

## Three misconceptions to correct first

### 1. The 20% volatility target is not a hard portfolio cap

The current formula is:

```text
base exposure × min(1, 20% / 20-day annualized volatility)
```

At B-tier base exposure 1.5x and volatility around 20%, nominal portfolio volatility is about 30%, not 20%. Three-day confirmation, the deadband and overnight gaps further separate executed risk from the target. Target exposure is capped at 1.5x, but observed exposure after price drift reaches about 1.54x.

This does not necessarily require an immediate rule change, but reports and risk management must describe it clearly. To keep portfolio volatility near 20%, test a hard-budget version that accounts for base leverage before limiting final exposure. Preliminary results are full-period CAGR 13.8%/drawdown -24.2%, and last-five-year 15.6%/-20.6%. Both risk and returns fall; this is not a free improvement.

### 2. Three-day confirmation delays cuts during fast declines

During COVID, raw targets fell from 1.50x to 0.85x and then 0.50x, while three-day confirmation and the 0.15x deadband kept executed exposure at the old tier. The design reduces sideways churn but retains excessive risk when volatility rises abruptly.

Simply cutting exposure after one or two days is not a clear improvement: recent results look better, but full-period CAGR falls to about 13.4%, turnover rises to about 11.8x, and 2011 losses worsen. The issue is not that shorter confirmation is always better; increasing and reducing exposure may need separate channels.

### 3. There are too few events to justify adding conditions

The oversold RSI floor triggered only 7 new events in actual QQQ history. RSI bottomed near 27 during the 2020 crash and never triggered it. That one event cannot justify raising the RSI threshold. Keeping RSI≤25 and the 0.15x floor is more prudent for now.

## Candidate comparisons already completed

All candidates use identical data, T+1 opening execution and 5bp costs. These are historical in-sample diagnostics, not forward evidence.

| Candidate | Full-period CAGR / maximum drawdown | Last-five-year CAGR / maximum drawdown | Assessment |
|---|---:|---:|---|
| V1.6.1 baseline | 15.0% / -26.9% | 16.8% / -21.8% | Current benchmark |
| Remove MACD | 15.2% / -27.6% | 18.2% / -21.2% | Worth separate forward validation |
| Cut after 2 days, add after 3 days | 13.4% / -27.8% | 16.1% / -20.4% | Not ready for adoption; higher turnover |
| Cut after 1 day, add after 3 days | 13.4% / -24.6% | 15.9% / -21.7% | Not ready for adoption; much worse in 2011 |
| Hard final-exposure 20% volatility budget | 13.8% / -24.2% | 15.6% / -20.6% | Risk-first tradeoff, not a return improvement |
| Fixed 20% QQQ core floor | 14.5% / -36.7% | 16.4% / -24.4% | Unattractive risk/return tradeoff |

Removing MACD slightly improves results, but the advantage is small and changes both E/R confirmation and bullish scoring. It does not prove MACD is useless. At most, it is a candidate requiring frozen rules and fresh validation.

## Recommended order of work

### First: lock down execution and reporting methodology

1. Python, daily checks and Pine must explicitly use closing signals and next-trading-day opening fills.
2. Record raw signal targets, confirmed targets, actual opening weights, drifted exposure and trading costs separately.
3. Define whether 1.5x is a target cap or an actual hard cap including price drift. The latter needs protection before allocation transitions.
4. QQQ, QLD, half-allocation and cash benchmarks must share T+1 execution, interest, costs and rebalancing assumptions.

This is the most valuable engineering work because it prevents execution differences from being mistaken for strategy advantages and improves confidence more than another indicator.

### Second: validate only one no-MACD candidate

Freeze V1.6.1 as baseline. Keep RSI, 4%/1% hysteresis, R, confirmation days and deadband unchanged. Test no-MACD separately using chronological rolling tests covering CAGR, maximum drawdown, Calmar, rolling relative performance versus QQQ, turnover and worst months.

If no-MACD wins only recently but fails in 2007-2012 or 2013-2019, keep V1.6.1 rather than upgrade based on one strong period.

### Third: test a separate risk-reduction channel

Keep three-day confirmation for increases. Permit an earlier small cut only when volatility rises rapidly, price suffers a large one-day break or actual exposure exceeds its risk budget. Separate this from trend signals and fix triggers and maximum cuts in advance.

This targets the 2020 delay while avoiding repeated cuts in sideways periods such as 2011. Reliable out-of-sample validation has not been completed, so it must not enter production directly.

### Fourth: consider a genuine 20% risk budget

If drawdown control is the priority, continue testing the hard volatility budget. If long-term returns are the priority, present results do not support immediate adoption. Do not simultaneously change volatility targeting, confirmation and the floor; that would obscure attribution.

## Overfitting assessment plan

Earlier parameter evolution reused the same history. Existing training/testing therefore cannot strictly be called untouched out-of-sample validation. Use a fixed process next:

1. Freeze V1.6.1 and at most 1–2 candidates; stop selecting parameters from full-history results.
2. Use rolling chronological splits: train 1999-2010/test 2011-2014, then train through 2014/test 2015-2018, and continue forward.
3. Compute indicators from full history and preserve real holding state in every test segment. Never reinitialize macro state, warm-up or capital at split points.
4. Consider upgrades only with consistent direction across all test segments. Also report doubled costs, one-to-two-day delays and worst rolling three-year results.
5. Use paired block resampling to estimate uncertainty versus QQQ; retain complete daily order ledgers and price-data hashes.

## Current decision

This assessment changes neither V1.6.1 nor production deployment. A future research switch should first complete strict rolling validation for no-MACD and separate risk reductions, then determine whether V1.6.2 is justified.

Local data ends on 2026-07-30 and is not current market data for 2026-09-07. Historical backtests are for research and education, not a guarantee of returns. Leveraged ETFs retain daily-reset, volatility-drag, slippage, tax, fee and liquidity risks.
