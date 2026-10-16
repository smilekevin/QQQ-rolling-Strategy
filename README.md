# QQQ / QLD Dynamic Allocation — Backtest and Reporting Pipeline

A strategy that uses technical indicators (MACD / RSI / Supertrend + a 250-day trend gate) to switch dynamically between **cash → a small QQQ allocation → all QQQ → QQQ+QLD (maximum target 1.5x)**, with a full historical backtest and an interactive HTML report.

Current report version: **V1.6.1a**; current strategy version: **V1.6.1**. Report updates cover presentation and observation markers only, without changing strategy rules or backtest methodology.

---

## 1. Files

| File | Purpose | Output |
|---|---|---|
| `1_prepare_data.py` | Download ^NDX/QQQ/QLD/^IRX/^VIX, warm up indicators with NDX and synthesize pre-2006 QLD | `prices.csv` |
| `indicators.py` | Shared indicators (MACD/RSI/Supertrend/regime gate), decision tiers and panic observation markers, reused by the backtest and daily check | — |
| `execution.py` | Shared T+1 opening execution engine, reused by backtesting, optimization and ablation | — |
| `2_backtest.py` | Calculate indicators, run the V1.6.1 backtest and export results | `results.json` |
| `3_generate_report.py` | Generate data for the fixed interactive HTML shell | `report_data.js` |
| `_headers` | Cloudflare static-asset cache rules to keep the HTML shell and daily data in sync | — |
| `daily_check.py` | Calculate the post-close target exposure and suggest holding or rebalancing | Terminal output |
| `README.md` | This guide | — |

> `opt.py` is an optional parameter-robustness and training/validation script; see Section 5.

Historical research reports are indexed in [`research/`](./research/README.md), covering strategy reassessment, cross-asset allocation, market breadth, momentum and QLD exposure windows. Each report retains its own data cutoff. Research candidates have not been adopted into the production strategy.

## 2. Running the pipeline

```bash
# Install dependencies once
pip install yfinance pandas numpy

# Run in order; all three scripts write beside their source files
python 1_prepare_data.py      # Download market data; approximately 10 seconds
python 2_backtest.py          # Backtest; approximately 5 seconds; print metrics
python 3_generate_report.py   # Generate report_data.js (daily data; not committed)

# Open the report
open qqq_qld_report.html      # macOS; double-click the file on Windows
```

Rerun these three steps to refresh the latest trading day. `qqq_qld_report.html` is a fixed page shell; daily data lives in the gitignored `report_data.js`, alongside the ignored `prices.csv` and `results.json`. Deploy `_headers` with the HTML so browsers and Cloudflare revalidate daily data. The page generates an hourly Shanghai-time cache key, `report_data.js?v=1.6.1a-YYYY-MM-DD-HH`. The HTML does not need an hourly update; keep the `1.6.1a` cache version synchronized when the report version changes.

The report defaults to English. On a first visit, a browser whose preferred language is Chinese (`zh`, including regional variants) sees Chinese. The **EN / Chinese switch at the top right** changes the whole report, including charts, tooltips, live indicators and explanatory text. A manual choice is remembered in local storage and takes priority on later visits. Switching languages preserves the selected periods and chart ranges. When storage is unavailable, the switch still works for the current page.

See [`CLOUDFLARE_DEPLOY.md`](./CLOUDFLARE_DEPLOY.md) for automatic daily deployment. [GitHub Actions](./.github/workflows/update-report.yml) builds and deploys `main` directly at 06:30 Beijing time Tuesday–Saturday (`30 22 * * 1-5` UTC), with a manual Run workflow option. Add repository Actions secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; no Worker runtime Secret or Deploy Hook URL is needed. After a successful manual run, remove the old Cloudflare Cron. Cloudflare still hosts `dist/` and provides push deployments and PR previews. The build command remains `bash build_cloudflare.sh`, deployment `npm run deploy`, and configuration `wrangler.jsonc`. The workflow verifies the published report matches its build. Scheduled starts may be delayed by GitHub; strategy rules are unchanged.

## 3. Strategy logic (V1.6.1)

**Signals are generated at the close of T and executed at the T+1 open, without look-ahead.** Existing holdings first absorb overnight returns; the portfolio rebalances at the open, then new holdings earn intraday returns.

The report separately marks **RSI(14)≤25 and VIX≥30** as extreme panic. This observes current and historical sentiment only; it never enters allocation, confirmation, deadband or rebalancing calculations.

1. **Macro gate with hysteresis**: exit the bullish regime below the **250-day moving average**. Once bearish, require a move **1%** above the average to turn bullish again, filtering false breakouts near the average.
2. **Bearish regime**:
   - **Deep bear**: price **4%** below the 250-day average, MACD line < 0 and bearish Supertrend → default **100% cash**, earning short-term Treasury interest.
   - **RSI(14)≤25** activates an oversold-floor latch in the bearish macro regime. Thereafter retain at least **0.15x QQQ** until the macro regime turns bullish. The floor is unleveraged; it is labeled F in a deep-bear state.
   - Without deep-bear conditions, **bullish Supertrend and MACD histogram > 0** → **reversal-recovery R: base 0.75x, then volatility scaling**. Deep-bear conditions have priority, so R cannot override E/F.
   - Otherwise use **mild-pullback D: base 0.5x (QQQ+cash), then volatility scaling**. Since V1.3, greater turbulence reduces exposure toward cash; actual exposure is approximately 0.15–0.5x.
3. **Bullish regime**: momentum score (0–4) = `bullish Supertrend + positive MACD histogram + positive MACD line + RSI>50`.
   - 0–2 points → **all QQQ (1.0x)**; 3–4 → **QQQ+QLD (1.5x)**.
   - **The highest base tier is 1.5x** (`MAX_EXPOSURE=1.5`). The former all-QLD 2x tier was removed after tests found no useful risk premium and no material return cost from removal.
   - 1.5x also requires **leverage eligibility**: a rising 250-day average **and** 20-day annualized volatility < 40%.
4. **Volatility targeting (core risk control)**: final net exposure = tier exposure × `min(1.0, 20% / 20-day realized annualized volatility)`. The default target range is 0–1.5x; scaling only reduces exposure. Volatility spikes automatically cut leverage, which is central to reducing drawdowns.
5. **Execution**: round exposure to 0.05 increments and require 3 consecutive days of confirmation; then apply a **0.15x deadband** (`DEADBAND`: no rebalance when target exposure differs from current holdings by <0.15x). Cash earns ^IRX interest; each rebalance costs 5bp per side. Full-period target exposure switches approximately 13.0 times/year.

Volatility scaling makes actual net exposure **continuous from 0 (cash) to a 1.5x target**. The six B/C/R/D/F/E decision tiers alone do not describe the actual holdings.

## 4. Backtest results (1999-03 onward, including costs)

| Portfolio | CAGR | Total return | Maximum drawdown | Calmar | Sharpe |
|---|---|---|---|---|---|
| **V1.6.1 strategy** | **14.9%** | **4388%** | **−26.9%** | **0.55** | **0.82** |
| QQQ buy and hold | 10.6% | 1466% | −83.0% | 0.13 | 0.51 |
| QLD buy and hold | 9.9% | 1231% | −98.8% | 0.10 | 0.44 |

**Higher historical total return with a lower drawdown than QQQ (−27% versus −83%).** Since 2006, using actual QLD data throughout, CAGR is 17.3%, maximum drawdown −26.9% and Calmar 0.64; the last five years are approximately 16.3%/−21.8%/0.74. With the 0.15x deadband, annualized target switching is about 13.0 times, one-way turnover 8.35x and average net exposure 0.97x.

> **Warm-up methodology:** QQQ listed on 1999-03-10 and lacks 250 pre-listing trading days. ^NDX (Nasdaq-100 Index) OHLC from 1997-01 until listing is scaled to QQQ’s first closing price and used only to warm up SMA/MACD/RSI/Supertrend/volatility. All returns start with actual QQQ opening data on 1999-03-11. Waiting for QQQ’s own SMA250 to mature on 2000-03-03, without NDX, gives a conservative reference of CAGR 13.2%, drawdown −26.9% and Calmar 0.49. Consider both; differences in warm-up are not strategy improvements.

V1.4 added asymmetric hysteresis for the sideways period from 2015-06 to 2016-07. Its local maximum drawdown fell from approximately −25.3% to −17.3%. The full-period parameter plateau was roughly a 3.5%–4.75% deep-bear threshold and a 0.5%–1.5% bullish re-entry threshold; the chosen **4% / 1%** is easier to explain. Local drawdowns in 2018 and the 2020 pandemic became slightly worse, so the change does not dominate in every market regime.

V1.5 added R reversal recovery to address underexposure during V-shaped rebounds in 2011, 2016 and 2025. With a bearish macro regime but bullish Supertrend and MACD histogram, base exposure rises from 0.5x to 0.75x before volatility scaling. The 0.70–0.80x range produces similar results. It reduces, but does not eliminate, underperformance versus QQQ during sharp rebounds.

V1.6 added an oversold RSI floor in bearish macro regimes: RSI(14)≤25 latches a minimum 0.15x until the macro regime turns bullish. It retains unleveraged QQQ and does not replace the R tier. Structural comparisons improved with either R alone or the floor alone; together they reached 14.9% CAGR and −24.7% drawdown under the earlier execution model, indicating complementary roles. Results are stable around RSI thresholds 23–25 and a 0.15x floor; higher thresholds or floors above 0.30x substantially increase drawdowns.

V1.6.1 changes no signal or allocation parameters. It corrects execution: multiplying a T+1 target by the previous-close-to-current-close return wrongly assigns an untradeable overnight gap to new holdings. The corrected order is existing holdings overnight → rebalance at the T+1 open → new holdings intraday. Full-period CAGR is largely unchanged, but maximum drawdown is honestly corrected from −24.7% to −26.9%.

> **Rebalancing:** QQQ/QLD weights drift freely while a tier is held. Rebalance only when the strategy changes its allocation, charging 5bp on actual trades. This matches the intended live process and minimizes turnover. Tests found a long-term difference of <0.03pp versus daily rebalancing to target weights, which is negligible.

## 5. Parameter research and overfitting

All tunable parameters are in `CONFIG` at the top of `2_backtest.py`.

- **Train in-sample and validate out-of-sample:** `opt.py` reports each parameter set separately for training (≤2012) and validation (2013+). Both must perform reasonably.
- **Find plateaus, not peaks:** neighboring values should work similarly. `SMA_LEN` performs well at 250/300, so 250 was chosen. `VOL_TARGET` from 0.14–0.25 produces similar results.
- **Change little, with a reason:** stacking individually optimal parameters often performs worse than changing one; this is overfitting.
- **Recognize limits:** maintaining leverage through both the 2000/2008 crashes while demanding high returns is unrealistic. V1.6.1’s approximately −27% drawdown relies heavily on the trend gate and volatility scaling working together.

Run `python opt.py` after generating `prices.csv`. It prints the volt×VOL_CAP grid under V1.6.1 opening execution, one-dimensional sensitivities, hysteresis scans around 4%/1%, R-tier exposure sensitivity and an RSI threshold×floor grid.

### Daily post-close execution (`daily_check.py`)

```bash
python daily_check.py                 # Target exposure and QQQ/QLD/cash allocation
python daily_check.py --current 0.66  # Supply current net exposure for hold/rebalance guidance
```

Execution discipline avoids trading every small daily fluctuation:

- **Rebalance at key boundaries:** invested ↔ cash, or unleveraged ↔ QLD leverage (the 1.0 boundary).
- **Within the same region:** rebalance only when target and current exposure differ by **≥0.15x**; otherwise hold.
- Daily checks are acceptable and produced the shallowest backtest drawdowns. Actual changes are around 12–15 times/year, averaging once every two or three weeks.

## 6. Data and methodology

- **Sources:** yfinance QQQ / QLD / ^NDX / ^IRX / ^VIX. Backtests use adjusted QQQ/QLD opening and closing prices; QQQ highs/lows feed Supertrend. ^NDX supplies only pre-listing indicator warm-up, never returns; ^VIX supplies only panic observation markers.
- **Synthetic QLD:** QLD listed in 2006-06. Earlier returns use `2×QQQ daily return − (0.95% fee + short-term interest rate)/252`; overnight uses `2×QQQ overnight return`, with intraday inferred to reconstruct the synthetic daily return exactly. Overlapping daily returns correlate **0.996** with actual QLD; CAGR is optimistically biased by about **0.8%/year**. Post-2006 data uses actual opening and closing prices.
- **Risk-free rate:** ^IRX (13-week US Treasury yield) proxies QLD financing costs and cash income.
- **Sharpe** uses rf=0; Calmar = CAGR / |maximum drawdown|.

## 7. Disclaimer

This project is for research and education only, **not investment advice**. Historical backtests do not guarantee future returns. Leveraged ETFs such as QLD carry volatility-drag and daily-rebalancing risks; prolonged holding or sideways markets may substantially underperform the underlying index. Live trading also involves opening slippage, taxes, fees and liquidity costs that the backtest does not fully capture. You bear the risks of acting on this material.
