# Research Report Archive

This directory preserves historical strategy research, organized by report date. Each report retains its original data cutoff, backtest methodology, conclusions and limitations; interpret its results within that context.

| Date | Report | Topic |
|---|---|---|
| 2026-09-07 | [QQQ/QLD strategy reassessment](./STRATEGY_REVIEW_2026-09-07.md) | Volatility targeting, confirmation delays and a validation plan |
| 2026-09-08 | [Cross-asset allocation review](./CROSS_ASSET_REVIEW_2026-09-08.md) | Portfolio comparisons with gold, bonds and other assets |
| 2026-09-11 | [S5FI market breadth and QQQ rebounds](./BREADTH_REVIEW_2026-09-11.md) | Historical relationships between breadth, oversold conditions and rebounds |
| 2026-10-13 | [Momentum prediction and higher returns](./MOMENTUM_REVIEW_2026-10-13.md) | Momentum prediction and the risk/return tradeoff of higher exposure |
| 2026-10-13 | [Shorter QLD exposure windows](./QLD_WINDOW_REVIEW_2026-10-13.md) | Leveraged holding-period limits and drawdown exits |
| 2026-10-16 | [Initial SMA extension cap study](./SMA_EXTENSION_REVIEW_2026-10-16.md) | Historical stateless cap, shorter averages and trading frequency |
| 2026-10-16 | [SMA hysteresis and confirmation](./SMA_HYSTERESIS_REVIEW_2026-10-16.md) | Final 15%/10% latch with fast overheat cuts; confirmed restoration, timing and cost comparisons |

On 2026-10-13, the user decided to retain existing V1.6.1 rules and parameters. On 2026-10-16, the user initially adopted the confirmed SMA250 +15% cap, then selected 15%/10% hysteresis with fast overheat cuts and confirmed restoration as the final V1.7.0 rule. Other research candidates remain unadopted. See the root [CLAUDE.md](../CLAUDE.md) for the current strategy definition.

Reproduction commands in the reports assume the repository root as the working directory. Related research scripts remain local; the archive commit included reports only. Market-data caches, temporary research outputs and daily report data do not belong in this directory. Use `TOPIC_REVIEW_YYYY-MM-DD.md` for future reports and update this index.
