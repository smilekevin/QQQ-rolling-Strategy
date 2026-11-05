"""Small predeclared grid, development-only selection, frozen chronological testing."""
from dataclasses import replace
import hashlib
from itertools import product
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .strategy import (DEVELOPMENT_END, TRAIN_END, Parameters, Strategy,
                       benchmark, config_dict, metrics, period_metrics)


def candidates(phase="extended"):
    """144 initial candidates plus 108 explicitly exploratory core variants."""
    for family, sma, vol, cap, confirmation in product(
            ("multi_indicator", "trend"), (150, 200, 250),
            (.12, .16, .20, .24), ("off", "10/7.5", "15/10"), (1, 3)):
        yield Parameters(family=family, sma_len=sma, vol_target=vol,
                         extension_enabled=cap != "off",
                         extension_threshold=.15 if cap == "15/10" else .10,
                         extension_release=.10 if cap == "15/10" else .075,
                         confirm=confirmation)
    if phase == "initial":
        return
    for sma, vol, core, cap, confirmation in product(
            (150, 200, 250), (.16, .20, .24), (.5, .75, 1.), (False, True), (1, 3)):
        yield Parameters(family="core_trend", sma_len=sma, vol_target=vol,
                         mild_exposure=core, extension_enabled=cap,
                         extension_threshold=.15, extension_release=.10,
                         confirm=confirmation)


def neighbor(a, b):
    """Immediate grid neighbors within a fixed model family and confirmation."""
    if (a.family, a.confirm) != (b.family, b.confirm):
        return False
    changed = [key for key in ("sma_len", "vol_target", "cap", "core")
               if axis(a, key) != axis(b, key)]
    return len(changed) <= 1 and (not changed or abs(axis(a, changed[0]) - axis(b, changed[0])) <= 1)


def axis(p, key):
    if key == "sma_len":
        return (150, 200, 250).index(p.sma_len)
    if key == "vol_target":
        return (.12, .16, .20, .24).index(p.vol_target)
    if key == "core":
        return (.5, .75, 1.).index(p.mild_exposure)
    if p.family == "core_trend":
        return int(p.extension_enabled)
    return 0 if not p.extension_enabled else (1 if p.extension_threshold == .10 else 2)


def select(frame, output, phase="extended"):
    """No price, indicator, return or score after DEVELOPMENT_END enters selection."""
    development = frame.loc[:DEVELOPMENT_END]
    engine = Strategy(development)
    baseline = benchmark(development)
    base_train = metrics(baseline.returns.loc[:TRAIN_END])
    base_validation = metrics(baseline.returns.loc["2010-01-01":])
    # The user's objective is return above SPY, without a requested 35% risk cap.
    # Keep the first phase's defensive budget for comparison. The return-oriented
    # extension accepts drawdowns up to SPY's development-period maximum, and
    # reports that extra risk explicitly rather than discarding core allocations.
    drawdown_limit = (.35 if phase == "initial" else
                      abs(min(base_train["mdd"], base_validation["mdd"])))
    rows, configs = [], list(candidates(phase))
    for index, p in enumerate(configs):
        result = engine.run(p)
        train = metrics(result.returns.loc[:TRAIN_END])
        validation = metrics(result.returns.loc["2010-01-01":])
        excess_train = train["cagr"] - base_train["cagr"]
        excess_validation = validation["cagr"] - base_validation["cagr"]
        worst_dd = min(train["mdd"], validation["mdd"])
        score = (min(excess_train, excess_validation)
                 + .25 * (excess_train + excess_validation) / 2
                 - .05 * max(0., abs(worst_dd) - .25))
        rows.append({"id": index, **config_dict(p), "train_cagr": train["cagr"],
                     "validation_cagr": validation["cagr"], "train_mdd": train["mdd"],
                     "validation_mdd": validation["mdd"], "train_excess": excess_train,
                     "validation_excess": excess_validation, "score": score,
                     "eligible": min(excess_train, excess_validation) > 0
                                 and worst_dd >= -drawdown_limit})
        if (index + 1) % 24 == 0:
            print(f"Development scan {index + 1}/{len(configs)}", flush=True)
    for row, config in zip(rows, configs):
        local = [r for r, p in zip(rows, configs) if neighbor(config, p)]
        row["neighborhood_score"] = float(np.median([r["score"] for r in local]))
        row["neighbor_success_rate"] = sum(r["eligible"] for r in local) / len(local)
        row["neighbor_count"] = len(local)
    stable = [r for r in rows if r["eligible"] and r["neighbor_success_rate"] >= .7]
    # Keep the failure visible. A best-effort candidate is still useful research,
    # but must not be labeled a robust outperformer if no candidate qualifies.
    pool = stable or [r for r in rows if r["eligible"]] or rows
    chosen = max(pool, key=lambda r: (r["neighborhood_score"], r["score"],
                                     r["family"] == "trend", -r["id"]))
    selection = {"parameters": config_dict(configs[chosen["id"]]),
                 "train_end": TRAIN_END, "selection_end": DEVELOPMENT_END,
                 "test_start": "2019-01-01", "candidate_count": len(configs),
                 "research_phase": phase,
                 "development_drawdown_budget": drawdown_limit,
                 "robust_qualifier_found": bool(stable),
                 "selection_metrics": {k: chosen[k] for k in (
                     "train_cagr", "validation_cagr", "train_mdd", "validation_mdd",
                     "neighbor_success_rate", "neighbor_count", "neighborhood_score")},
                 "data_cutoff": str(development.index[-1].date()),
                 "method": "Coarse grid, positive excess CAGR in train and validation, "
                           "drawdown within the recorded development budget, "
                           ">=70% qualifying immediate neighbors, "
                           "maximize median neighborhood score; no test-period tuning."}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output / "development_scan.csv", index=False)
    # Persist the exact choice before the final test evaluation.
    (output / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    return selection


def evaluate(frame, selection, metadata):
    p = Parameters(**selection["parameters"])
    engine = Strategy(frame)
    selected = engine.run(p)
    reference = Parameters(sma_len=250, vol_target=.20, bear_exit_buffer=.04,
                           lever_volceil=.40, extension_threshold=.15,
                           extension_release=.10)
    results = {"strategy": selected, "spy": benchmark(frame),
               "static_spy_sso": benchmark(frame, 1.5),
               "qqq_parameters_on_spy": engine.run(reference),
               "unleveraged_rule": engine.run(replace(p, max_exposure=1.)),
               "double_cost": engine.run(p, cost_bps=10.),
               "extra_day_delay": engine.run(p, delay=2)}
    report = {"selection": selection, "data": metadata,
              "metrics": {name: period_metrics(result) for name, result in results.items()},
              "annual": {}, "latest": {}, "caveats": [
                  "Historical chronological tests are not an untouched forward sample. "
                  "Initial adaptation diagnostics and the original QQQ research already used recent history.",
                  "SSO is synthetic before 2006-06-22; adjusted real SSO is used thereafter. "
                  "Synthetic financing is a Treasury proxy, not a tradable historical quote.",
                  "5bp per side includes an assumed allowance for fees/slippage; taxes, bid/ask "
                  "variation, real execution delays and capacity are not modeled.",
                  "Maximum 1.5x refers to targets; holdings can drift beyond target between trades. "
                  "Static 50/50 SPY/SSO is a buy-once drifting mix, not constant daily 1.5x."]}
    for name, result in results.items():
        report["annual"][name] = {str(year): metrics(group)
                                  for year, group in result.returns.groupby(result.returns.index.year)}
    returns = selected.returns
    spy_returns = results["spy"].returns
    beta = float(returns.cov(spy_returns) / spy_returns.var())
    report["risk"] = {"realized_beta_to_spy": beta,
                       "mean_opening_exposure": float(selected.exposure.mean()),
                       "max_opening_exposure": float(selected.exposure.max()),
                       "annual_one_way_turnover": float(selected.turnover.sum() * 252 / len(returns)),
                       "annual_rebalances": float((selected.turnover > 1e-12).sum() * 252 / len(returns))}
    ind = selected.indicators.iloc[-1]
    target = float(selected.signals.iloc[-1])
    weights = {"spy": target if target <= 1 else 2 - target,
               "sso": max(0., target - 1), "cash": max(0., 1 - target)}
    report["latest"] = {"date": str(frame.index[-1].date()), "next_open_target": target,
                         "target_weights": weights, "macro_bull": bool(ind.macro_bull),
                         "rvol": float(ind.rvol), "rsi": float(ind.rsi),
                         "sma": float(ind.sma),
                         "extension_cap_active": bool(p.extension_enabled and ind.extension_cap_active),
                         "last_executed_target": float(selected.signals.shift(1).iloc[-1]),
                         "last_opening_exposure": float(selected.exposure.iloc[-1])}
    report["selection_sha256"] = hashlib.sha256(
        json.dumps(selection, sort_keys=True).encode()).hexdigest()
    return report, results
