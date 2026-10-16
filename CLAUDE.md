# CLAUDE.md — Project Context and Design Decisions

> For future agents and maintainers: this document records strategy design, evolution, key analytical findings and pitfalls. Read it in full before changing code, especially **Consistency requirements**.

## 1. Project overview

A QQQ / QLD **dynamic allocation strategy** using QQQ technical indicators (MACD / RSI / Supertrend + a 250-day moving average) and volatility targeting to adjust exposure continuously between **cash → QQQ → QQQ+QLD (1.5x)**. Includes a full historical backtest from 1999 onward and an interactive HTML report. QLD targets 2× QQQ’s daily return.

Current report version: **V1.6.1a**; current strategy version: **V1.6.1**. Report updates affect presentation and observation markers only, without changing strategy rules or backtest methodology.

## 2. File structure

| File | Purpose |
|---|---|
| `1_prepare_data.py` | Download ^NDX/QQQ/QLD/^IRX/^VIX, warm up indicators with NDX and synthesize pre-2006 QLD → `prices.csv` |
| `indicators.py` | **Shared indicators:** ema/macd/rsi/supertrend/compute, decide_tier/DECNAME and extreme-panic observation; reused by the backtest and daily check |
| `execution.py` | **Shared execution:** existing holdings overnight → rebalance at the T+1 open → new holdings intraday; reused by backtest/opt/ablation |
| `2_backtest.py` | Indicators imported from indicators + V1.6.1 backtest → `results.json`; **top-level CONFIG is the only parameter-editing location** |
| `3_generate_report.py` | Update interactive report data → `report_data.js`; never rewrite the HTML |
| `qqq_qld_report.html` | Fixed interactive shell reading local `report_data.js`, with English/Chinese presentation |
| `_headers` | Cloudflare revalidation rules for `report_data.js`, preventing shell/data version mismatches |
| `daily_check.py` | Post-close target exposure and decision tier, with hold/rebalance guidance |
| `opt.py` | Parameter robustness and training/validation comparisons (vectorized, <1s) |
| `ablation.py` | Indicator ablation experiments |
| `research/` | Historical reports and date index; see [`research/README.md`](./research/README.md) |
| `.github/workflows/update-report.yml` | Daily/manual GitHub deployment of main; PR build validation only |
| `scripts/verify_deployment.py` | Verify the published report matches the current build |
| `README.md` | User-facing guide |

Pipeline order: `1 → 2 → 3`. `prices.csv`, `results.json` and `report_data.js` are gitignored and reproducible. The fixed `qqq_qld_report.html` is committed.

**Historical Cloudflare automatic deployment (2026-10-14, superseded for daily scheduling on 2026-10-16):** `build_cloudflare.sh` installs dependencies; `scripts/build_report.py` runs the existing pipeline in a temporary directory and validates current prices, report dates and series. Downloads/price validation allow three attempts. Success produces only static files in `dist/`: `index.html`, the original report HTML, `report_data.js` and `_headers`. Root `wrangler.jsonc` binds `dist/`; one `qqq-strategy-auto-deploy` Worker hosts the report and uses dashboard Cron to POST its own Workers Builds Hook. `cloudflare/worker.mjs` validates the runtime Secret `DEPLOY_HOOK_URL` as a Workers Builds address and checks the returned build ID; HTTP requests only read ASSETS. Assets have priority and `_headers` remains effective. `package.json` pins Wrangler. Production uses `npm run deploy` (`wrangler deploy`). Omitting preview/Cron fields preserves dashboard settings; omitted workers.dev may default to enabled, which the user accepts. Workers Builds separately uses `bash build_cloudflare.sh`. Dashboard Cron `30 22 * * MON-FRI` is 06:30 Beijing time Tuesday–Saturday, or 17:30 New York standard time / 18:30 daylight time. Same-day data validation requires at least 17:00 New York time. Replace the old Pages Hook with this Worker’s Builds Hook. See [`CLOUDFLARE_DEPLOY.md`](./CLOUDFLARE_DEPLOY.md). Deployment helpers do not change strategy, parameters, execution or data filling. The permissive seven-day staleness check is not an exchange calendar.

**Cloudflare SQLite compatibility fix (2026-10-14):** initial Workers Builds logs showed Python 3.12.10 installed, but all five yfinance/Peewee downloads failed without SQLite, and empty data then caused IndexError. `requirements.txt` pins `pysqlite3-binary==0.5.4.post2` on Linux x86_64. Peewee natively supports this fallback without rewriting the standard library or third-party source. Before downloading, `build_cloudflare.sh` runs `scripts/check_build_runtime.py` to create, write and read a table using the actual cache backend and print its version. Missing drivers fail immediately rather than retrying invalid downloads three times. This fixes build dependencies only.

**Cloudflare preview URL routing fix (2026-10-14):** PR #2’s branch and deployment preview URLs returned `404 / error code: 1042` while production worked. `preview_urls` controls the workers.dev route for Worker Previews as well as legacy Version URLs. Earlier guidance that false would not affect branch previews was wrong. The user now manages this switch only in the dashboard; the repository omits it and deployment does not explicitly change its existing state. Preview acceptance requires opening the page and report data, beyond build/deployment success.

**Production domain and dashboard configuration (user decision, 2026-10-14):** production is `https://qqq-strategy.kenzhu.link`, already bound by the user; the home page and `report_data.js` returned HTTP 200. Root config omits `workers_dev`, `preview_urls` and `triggers`. The user manages domains, previews and Cron in the dashboard. Production remains `npm run deploy` / `wrangler deploy`. Pinned Wrangler 4.150.0 preserves existing preview and scheduled-trigger settings when those fields are omitted. With no `workers_dev` or repository routes, production may re-enable workers.dev by default; the user explicitly accepts this and requested no extra version-publishing script. The original setup enabled Preview URL and configured Cron in the dashboard; the later GitHub Actions migration supersedes that daily schedule. The related change used `fix/cloudflare-preview-urls`; the user merges PRs manually.

**English documentation and bilingual report (2026-10-14):** all project Markdown is maintained in English. The report defaults to English, chooses Chinese when the browser’s first preferred language begins with `zh`, and offers an EN/Chinese switch at the top right. A valid saved manual preference overrides browser detection. Storage failures must not break rendering or switching. Switching updates static text, dynamic indicators, tables, chart labels/tooltips and errors in place while preserving selected periods/ranges. Data keys, numeric calculations and strategy rules remain unchanged. This work uses `feat/english-docs-bilingual-report`.

**GitHub Actions daily deployment (user decision, 2026-10-16):** `.github/workflows/update-report.yml` replaces Worker Cron/Deploy Hook scheduling. UTC `30 22 * * 1-5` runs from default `main` at 06:30 Beijing time Tuesday–Saturday; `workflow_dispatch` allows manual recovery on `main`. GitHub repository Actions secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` authenticate the credential-check/deploy steps only. Missing credentials fail production runs before building; PRs build/test/package without credentials or production deployment. Official setup Actions are pinned to commits. The workflow reuses the existing temporary-directory pipeline and pinned Wrangler, serializes production workflow runs, and verifies the entire published `report_data.js` payload against its build via `scripts/verify_deployment.py`, with cache-busting and bounded retries. A verification failure does not automatically roll back. Cloudflare Git-triggered production deployments and PR previews remain in place. The Worker only serves assets; a retained legacy `scheduled()` logs a migration notice without credentials or outbound calls. After the first successful manual run, the user removes old Cloudflare Cron and unused Hook settings. Do not add `triggers`, `workers_dev` or `preview_urls` to Wrangler. Ordinary dashboard variables can be replaced without `keep_vars`; encrypted Secrets are preserved by normal deployments. Daily deployment no longer uses runtime credentials. GitHub schedules can be delayed/dropped and public-repository schedules disable after 60 days without activity; document manual recovery rather than promising exact-time execution. See `CLOUDFLARE_DEPLOY.md` for setup. This change uses `feat/github-actions-scheduled-deploy`; only the user merges its PR.

## 3. Current strategy V1.6.1: complete rules

Decision chain: signal at the close of T, execution at the T+1 open, no look-ahead.

1. **Stateful macro gate with hysteresis:** exit the bullish regime below the **250-day moving average**. Once bearish, re-enter only above `SMA250 × 1.01`.
2. **Decision tiers (base/nominal exposure):**
   - **E — Deep bear/cash:** bearish macro regime, price below `SMA250 × 0.96`, MACD line < 0 and bearish Supertrend → default **0x cash**, earning Treasury interest. **Deep-bear conditions have priority over R.**
   - **F — Oversold floor:** those deep-bear conditions with the bearish RSI floor latch active → minimum **0.15x QQQ**, unleveraged, since V1.6.
   - **R — Reversal recovery:** bearish macro regime without deep-bear conditions, but bullish Supertrend and MACD histogram > 0 → base **0.75x** × volatility scaling, since V1.5; actual about 0.2–0.75x.
   - **D — Mild pullback:** bearish macro regime without deep-bear/R conditions → base **0.5x** × volatility scaling, since V1.3; actual about 0.15–0.5x.
   - **C — Neutral bullish:** bullish macro regime with 0–2 momentum points, or leverage blocked → base **1.0x**.
   - **B — Uptrend:** bullish macro regime, 3–4 momentum points, rising SMA250 and volatility <40% → base **1.5x**, the highest tier.
   - Momentum score = `bullish Supertrend +1, MACD histogram>0 +1, MACD line>0 +1, RSI>50 +1` (0–4).
3. **Volatility targeting (core):** final net exposure = base tier × `min(1.0, 20% / 20-day annualized volatility)`. **Scale down only**, with a 0–1.5x target cap. Volatility spikes cut leverage automatically, central to both drawdown control and historical returns.
4. **Oversold RSI floor latch:** RSI(14)≤25 during a bearish macro regime activates a **0.15x** minimum until the macro regime turns bullish. No leverage is added. R/D targets above 0.15x remain unchanged. The latch cannot activate before SMA250 is valid.
5. **Noise control:** asymmetric 0%/1% macro hysteresis; exposure rounded to 0.05 increments with 3 consecutive days of confirmation; then a 0.15x deadband.
6. **Execution order (V1.6.1):** after the T-close signal, existing holdings absorb overnight returns and cash interest. Rebalance to the new target at the T+1 open; new holdings earn open-to-close returns. Charge 5bp per side. **No rebalancing while a tier is held**: weights drift with prices and change only on allocation transitions.

**Extreme-panic observation, not a strategy rule:** `RSI(14)≤25 and VIX≥30` marks current/historical sentiment. It never enters decision tiers, target exposure, confirmation, deadband or trades and cannot change V1.6.1 returns.

**Key concept: net exposure is the portfolio volatility multiplier.** QLD and QQQ correlate 0.998, so portfolio volatility is approximately net exposure × QQQ volatility; 1.5x exposure is about 1.5× volatility, empirically checked. Volatility targeting therefore directly adjusts portfolio risk.

## 4. CONFIG parameters (top of `2_backtest.py`)

```text
SMA_LEN=250  BEAR_EXIT_BUFFER=0.04  BULL_REENTRY_BUFFER=0.01  RECOVERY_EXPOSURE=0.75
RSI_OVERSOLD=25  OVERSOLD_FLOOR=0.15
VOL_TARGET=0.20  VOL_CAP=1.0  MAX_EXPOSURE=1.5
ST_PERIOD=10 ST_MULT=3.0 RVOL_WIN=20 LEVER_VOLCEIL=0.40
CONFIRM=3 COST_BPS=5/10000 DEADBAND=0.15  (0.05–0.25 is insensitive; 0.15 reduces turnover)
```

## 5. Backtest results (1999-03 onward, costs included, no rebalancing within tiers)

| Period | CAGR | Maximum drawdown | Calmar | Sharpe |
|---|---|---|---|---|
| Full period | 14.9% | −26.9% | 0.55 | 0.82 |
| Since 2006 (actual QLD) | 17.3% | −26.9% | 0.64 | 0.91 |
| Since 2010 | 18.2% | −26.9% | 0.68 | 0.94 |
| Since 2020 | 18.5% | −26.9% | 0.69 | 0.88 |
| Last 5 years | 16.3% | −21.8% | 0.74 | 0.87 |

Benchmarks (CAGR/drawdown/Calmar): QQQ buy and hold 10.6%/−83%/0.13; QLD 9.9%/−99%/0.10. $10,000 over 27 years becomes about $449,000. Annualized exposure switching is about 13.0 times, one-way turnover 8.35x, and average net exposure approximately 0.97x.

**Warm-up methodology:** QQQ listed on 1999-03-10. `prices.csv` uses scaled ^NDX from 1997-01-02 until listing for `signal_close/high/low` only. QQQ/QLD opening-segment returns stay NaN during warm-up. Backtest/opt/ablation begin returns on the first executable real QQQ day, 1999-03-11. Starting instead when QQQ’s own SMA250 becomes valid on 2000-03-03, without NDX, gives 13.2%/−26.9%/Calmar 0.49. Warm-up differences are not strategy improvements.

## 6. Evolution: rationale and validation

- **Initial:** daily Supertrend alone → 33 switches/year and −84% drawdown; failed because of repeated leverage re-entry in bear-market rebounds.
- **Long-term gate + volatility targeting + deep-bear cash exit + interest on cash:** drawdown fell to −42% and Calmar doubled.
- **VOL_CAP 1.15→1.0:** scaling can only reduce exposure; drawdown improved with similar returns.
- **V1.1:** trend gate 200→**250 days**. opt.py found a plateau at 250/300 and improvement in both training/validation periods. Drawdown −42%→−32%.
- **V1.2:** removed the all-QLD 2x tier, `MAX_EXPOSURE=1.5`. Ablation found no useful risk premium from 2x at overheated points; removal cost no material return, sometimes improved it, and reduced turnover.
- **V1.3:** D changed from fixed 0.5x to **0.5x × volatility scaling**. Fixed 0.5 was too high. Scaling reduced drawdown −30%→−26%, Calmar 0.41→0.45, consistently across the full period and subperiods.
- **V1.4:** SMA250 asymmetric hysteresis: exit below the average; re-enter 1% above; E only 4% below with bearish indicator agreement; otherwise D. The 2015-06–2016-07 sideways period previously suffered about −25.3% drawdown from repeated cash exits and late re-entry; this fell to about −17.3%. Fine-grid peak was around 4%/0.5%, but 3.5%–4.75% / 0.5%–1.5% formed a plateau, so choose interpretable 4%/1%. Local 2018/COVID drawdowns became slightly worse.
- **V1.5:** added R reversal recovery in bearish regimes. In 2011, 2016 and 2025, volatility-scaled D averaged only about 0.2x and missed sharp rebounds. If E is absent and Supertrend/MACD histogram are bullish, restore base 0.75x without leverage. Annual returns changed approximately −9.2%→−8.4%, −3.9%→−2.6%, +4.9%→+5.7%. 0.70–0.80x is similar; select 0.75x. It reduces recovery delay but cannot guarantee keeping up with QQQ in V-shaped rebounds.
- **V1.6:** added the bearish RSI floor latch, minimum 0.15x after RSI(14)≤25 until bullish macro recovery; complements R without leverage. Structural comparisons (CAGR/drawdown/Calmar): no R/no floor 14.17%/−25.34%/0.559; R only 14.49%/−25.39%/0.571; floor only 14.49%/−24.91%/0.582; R+floor 14.94%/−24.73%/0.604. The mechanisms are complementary.
- **V1.6.1:** corrected execution only. The old shift(1) target multiplied by close-to-close returns wrongly included overnight gaps unavailable to new holdings. Split overnight/intraday: old holdings overnight → opening rebalance → new holdings intraday. Full CAGR stays near 14.9%; drawdown −24.7%→−26.9%, Calmar 0.60→0.55.

**Overfitting disclosure:** V1.1–V1.6 were progressively optimized on the same history. V1.4–V1.6 have explicit state-machine logic and parameter plateaus, but were still motivated by known historical problems. Forward Calmar is likely lower than the backtest’s 0.55. V1.6.1 adds no parameters and is an execution correction, not a new optimization.

## 7. Key analytical findings: avoid repeating prior research

- **User decision (2026-10-13):** retain V1.6.1 rules and parameters. Momentum, higher exposure and shorter QLD-window results remain research records; no candidate is adopted.
- **QLD-window study, 2026-10-13:** data through 2026-09-25, production unchanged. See [`QLD_WINDOW_REVIEW_2026-10-13.md`](./research/QLD_WINDOW_REVIEW_2026-10-13.md) and local `qld_window_research.py`. All confirmed targets ≤1x are unchanged; QLD exits substitute QQQ. The exploratory 20-day cap plus a 5% QQQ running-close-peak drawdown exit gives last-five-year CAGR/drawdown 17.17%/−19.60%, versus baseline 17.92%/−21.84%; since 2010, 17.77%/−24.87% versus 18.79%/−26.91%. Recent QLD holding-day share falls 44.1%→23.9%. The tradeoff persists with doubled costs and one extra execution day, but 2015–2018 drawdown does not improve and returns fall. The combination followed single-rule diagnostics and is not independent out-of-sample proof. The failed 2020 leverage window lasted only 13 trading days, so a 20-day cap cannot stop rapid failures; the 5% exit alone does not improve recent maximum drawdown. No QLD still draws down about 19.6% recently, showing substantial core QQQ risk. Holding days are not leveraged-ETF drag; do not time trades using hindsight window lengths or adopt this candidate automatically.
- **Momentum/return study, 2026-10-13:** data through 2026-09-25, production unchanged. See [`MOMENTUM_REVIEW_2026-10-13.md`](./research/MOMENTUM_REVIEW_2026-10-13.md) and local `momentum_research.py`. Fixed annual walk-forward ridge regression did not establish stable incremental predictive value from five-day MACD/RSI changes. The user accepts more risk. Raising eligible C from 1x to 1.25x only when `lever_ok` holds, keeping B at 1.5x, gives since-2010 19.67%/−32.55% versus baseline 18.79%/−26.91%. It fails in 2019–2022 and recent gains are sensitive to one extra execution day. Uniform B=2x substantially increases turnover. These are exploratory historical risk/return comparisons, not an upgrade decision; never wire them directly into production.
- **V1.6.1 ablation:** full strategy about 14.9%/−26.9%/Calmar 0.55; no MACD 15.1%/−27.6%/0.55; no RSI (also removing the floor) 13.1%/−26.9%/0.49; no Supertrend 12.9%/−26.9%/0.48. Full indicators do not maximize each isolated metric, but balance risk/return. MACD/Supertrend also confirm E/R direction.
- **Parameter sensitivity:** volt (0.14–0.25), vcap and lev_volceil are insensitive plateaus; SMA=200–300 and confirm=3 are favorable. V1.4 deep-bear 4%–4.5% and re-entry 0.5%–1.5% remain plateaus. V1.5 R base 0.70–0.80x is similar. V1.6 RSI 23–25 and floor 0.15–0.20x are viable; thresholds ≥27 with higher floors substantially worsen results. Selected training/validation Calmar is about 0.42/0.71. **Do not chase isolated peaks.**
- **D=0x versus D=0.5x × volatility:** old full-period differences depended heavily on the 1999 warm-up. After correction, do not reuse the old 0.93pp/96% figures. Since-2010 similarity is unchanged. Keep volatility-scaled D; rerun on new data before discussing simplification.
- **Execution frequency:** daily post-close checks suffice; daily checks gave the shallowest backtest drawdown. About 13.0 target switches/year. Always rebalance across cash/leverage boundaries; within a region, require ≥0.15x deviation. Waiting more than two weeks worsens drawdowns.
- **Rebalancing:** weights drift within tiers; rebalance only on allocation changes. Difference versus daily rebalancing is <0.03pp, negligible. Mixed holdings cover only about 17% of time, with small drift.

## 8. Clarifications

- **Decision tier ≠ final exposure:** B/C/R/D/F/E describe strategy states; volatility scaling, the floor, confirmation and deadband still apply. R base 0.75x can scale to 0.4x; F means the deep-bear 0.15x floor latch is active.
- **Equity colors encode decision tiers:** green uptrend, gold neutral bullish, blue reversal recovery, red mild pullback, purple oversold floor, gray deep bear/cash. **Actual exposure is in tooltips.** The distribution chart counts tier time.
- **Confirmation delay:** after a tier switch, latest-decision colors lead executed exposure by 3–4 trading days. On 2023-05-15, uptrend with 1.0x was caused by incomplete three-day confirmation, not volatility scaling (about 16% then). This is intentional.
- **Macro state is path-dependent:** 0.5% above SMA250 stays bullish if previously bullish, but stays bearish until +1% if previously bearish. Never reconstruct `macro_bull` from `price > sma` alone.
- **Initial valid SMA:** `macro_regime()` initializes using `price >= sma`, then applies 0%/1% hysteresis. NaN warm-up days are not executable D-tier days.
- **Observed exposure ranges:** B 0.75–1.5x (median 1.5), C 0.22–1.0x (median 1.0), R about 0.2–0.75x, D 0.15–0.5x, F 0.15x, E 0x. C near 0.2x requires annualized volatility around 90% (only 2000/2020); B near 0.75x around 40% (2000/2015/2020).

## 9. Consistency requirements

- **Dashboard configuration takes priority:** never re-add `workers_dev`, `preview_urls` or `triggers` to Wrangler. Production remains `npm run deploy` / `wrangler deploy`, previews `npm run preview`. The user maintains domains and Preview URLs in the dashboard and accepts default workers.dev re-enabling. After GitHub Actions migration, the user removes the legacy Cron in the dashboard. Omitted preview/Cron fields should preserve dashboard state; do not promise omitted settings keep workers.dev disabled.
- **Git delivery (user decision, 2026-10-14):** start each task from latest `main` on a purpose-named feature branch, such as `feat/...` or `fix/...`; no mandatory branch named `preview`. The earlier preview feature used `feat/cloudflare-preview`. Commit, push and create/update a PR to `main` with Cloudflare build status and preview comments. Non-production builds use `npm run preview`. Verify the exact commit’s build, date and page. **The user merges manually in the PR.** Codex handles branches, commits, pushes, PRs and validation; never merge, enable auto-merge or push directly to `main`. Without remote build results, leave the feature branch. Production and scheduled GitHub deployments remain on `main`. Root `previews: {}` uses only branch assets, without production credentials or Cron. The user handles Cloudflare dashboard settings; see [`CLOUDFLARE_DEPLOY.md`](./CLOUDFLARE_DEPLOY.md).
- **English documentation, bilingual presentation:** maintain all project Markdown in English. The report must support English and Chinese for every visible label, tooltip, explanation and error. Saved manual preference takes priority over the first browser language. Keep the original Chinese data keys used by the Python pipeline; translate display labels only. Switching must preserve numeric values, selected periods, dates and chart ranges. Keep the HTML self-contained so both local-file opening and the current static build continue to work.
- **Shared indicators/state machine/latch/tiers:** `2_backtest.py` and `daily_check.py` import `indicators.py`. `macro_regime()` and `oversold_latch()` must evolve over complete history; no latch before SMA validity. `deep_bear` is `price < sma × (1-BEAR_EXIT_BUFFER)`; E/F also require negative MACD and bearish Supertrend. **Post-decision exposure mapping** (score→base, volatility scaling, floor, confirmation, deadband) remains separately in both scripts’ `targets()`/main loop; changes must stay synchronized. `opt.py`/`ablation.py` inline rules for parameter scans and must also be updated when rules change.
- **Shared execution:** backtest/opt/ablation must call `execution.run_next_open()`: existing holdings T→T+1 overnight and cash interest → opening rebalance/costs → new holdings open→close. Never copy a close-to-close execution loop.
- **Warm-up/trading boundary:** `signal_close/high/low` may include pre-listing NDX proxies, but `qqq/qld_overnight_ret` and `qqq/qld_intraday_ret` must be NaN there. Calculate indicators, confirmation and shift(1) on full signal history, then restrict returns with `execution.valid_trade_index()`. Never include NDX returns in portfolio returns.
- **Synthetic pre-2006 QLD:** overnight = `2×QQQ overnight return`; infer intraday from the total daily return so `(1+overnight)*(1+intraday)-1 == qld_ret`. After listing, use actual adjusted opening/closing prices.
- **Colors/distribution use decision tiers**, never exposure bins; the former `band()`/`tier()` were removed. Earlier exposure-bin `<`/`<=` boundaries disagreed at 0.75, causing classification errors. `decide_tier` is now the single definition.
- **Tier definitions must match targets():** B only for `macro_bull and s>=3 and lever_ok`. In bearish regimes, first check `deep_bear and MACD<0 and bearish Supertrend`: F if latch active, E otherwise. Without deep-bear conditions, bullish Supertrend and MACD histogram>0 gives R; otherwise D. **Deep-bear priority must not be overridden by R.** If the latch raises D/R exposure, the tier name remains D/R.
- `STATECOL` keys must exactly match `results.json`’s `dist` tier-name keys, otherwise distribution colors break. Translate rendered chart labels without altering key-based color lookups.
- **Extreme panic is observation only:** `indicators.extreme_panic()` defines `RSI≤25 and VIX≥30`, shared by the backtest/daily check. Export only `panic_dates` / `latest.extreme_panic`; never use it in targets, confirmation, deadband or execution.
- **Fixed HTML shell:** only Chart.js loads from CDN. `3_generate_report.py` writes daily gitignored `report_data.js`, never HTML. Daily series have about 6880 points and approximately 350KB, growing with history. Drawdown and yearly return/drawdown derive from equity in the browser; exposure and tooltips share `state_exp`; do not store redundant annual data. Annual returns use prior-year-end to current-year-end equity. Calendar-year drawdown starts from prior-year-end equity, including January declines.
- **Drawdown ranges:** independent full/after-2008/2015/2020/2022 and custom ranges. Slice equity first, then calculate within-range running peaks. First day is 0%; no pre-range drawdown carries in. Start advances to the first available day, end retreats to the last. If no data, retain the chart and show a localized message.
- **Cache consistency:** deploy `_headers` with HTML to revalidate `report_data.js`. Shanghai-time hourly keys use `report_data.js?v=1.6.1a-YYYY-MM-DD-HH`, limiting stale data to the same hour even if intermediate caches ignore headers. HTML is not updated daily; synchronize its `1.6.1a` key on version changes. Detect the strategy key from `R.metrics`; never hardcode its versioned name, to tolerate short shell/data publication races.
- **Export contract:** `results.json` contains dates / equity{strategy,qqq,qld,blend,half} / state_exp / decision(B/C/R/D/F/E) / panic_dates / dist / metrics(full,since-2006,2010,2020,last-five-years) / latest. `latest` includes `executed_exp` (currently executed), `exp` (next-open target), `sma250`, `macro_bull`, `deep_bear`, `oversold_latch`, `vix`, `extreme_panic`. Equity colors use decision; tooltips display actual `state_exp`.

## 10. Data and disclaimer

- Sources: yfinance QQQ / QLD / ^NDX / ^IRX / ^VIX. ^NDX is scaled to QQQ’s first closing price for pre-listing warm-up only, switching to actual QQQ OHLC after listing. ^VIX is observation only. QQQ/QLD use adjusted opening/closing prices. **QLD listed in 2006-06**; earlier returns use `2×QQQ daily return − (0.95% fee + short-term rate)/252`. Correlation with actual QLD daily returns is 0.996 and CAGR is optimistically biased about 0.8%/year. Since 2006, actual data is used.
- Sharpe uses rf=0; Calmar = CAGR / |maximum drawdown|.
- **Disclaimer:** research and education only, not investment advice. Historical backtests do not predict future results. Leveraged ETFs have volatility-drag and daily-reset risks and can substantially underperform in long holding periods or sideways markets. Live opening slippage, taxes, fees and liquidity costs are not fully modeled.
