"""Run with python -m spy_strategy (from the repository root)."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .data import DEFAULT_OUTPUT, load_prices
from .research import evaluate, select


def write_outputs(report, results, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    (output / "results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    pd.DataFrame({name: result.equity for name, result in results.items()}).to_csv(
        output / "equity.csv", index_label="Date")
    selected = results["strategy"]
    pd.DataFrame({"close_target": selected.signals,
                  "open_target": selected.signals.shift(1),
                  "opening_exposure": selected.exposure,
                  "turnover": selected.turnover}).to_csv(output / "signals.csv", index_label="Date")
    chart = {"dates": [str(d.date()) for d in selected.equity.index],
             "equity": {key: [float(v) for v in results[key].equity]
                        for key in ("strategy", "spy", "static_spy_sso")},
             "exposure": [float(v) for v in selected.exposure]}
    template = Path(__file__).with_name("report_template.html").read_text()
    payload = json.dumps({**report, "chart": chart}, ensure_ascii=False, allow_nan=False)
    html = template.replace("/* REPORT_DATA */", payload.replace("<", "\\u003c"))
    (output / "spy_report.html").write_text(html)


def print_results(report, output):
    for period in ("full", "train", "validation", "holdout", "actual_sso"):
        print(f"\n{period:18}  CAGR     max DD")
        for name in ("strategy", "spy", "static_spy_sso"):
            m = report["metrics"][name].get(period)
            if m:
                print(f"{name:18} {m['cagr']:7.2%} {m['mdd']:9.2%}")
    print("\nNext-open target:", report["latest"])
    print("Development robustness gate:", report["selection"]["robust_qualifier_found"])
    print("Report:", Path(output).resolve() / "spy_report.html")


def main():
    parser = argparse.ArgumentParser(description="Independent SPY/SSO strategy research")
    parser.add_argument("command", choices=("prepare", "research", "backtest"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--refresh", action="store_true", help="Refresh adjusted Yahoo prices")
    parser.add_argument("--as-of", help="Completed NYSE session, YYYY-MM-DD; default latest")
    parser.add_argument("--phase", choices=("initial", "extended"), default="extended")
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).with_name("selected.json"))
    args = parser.parse_args()
    frame, sources, metadata = load_prices(args.output, args.refresh, args.as_of)
    print(f"Completed data cutoff: {metadata['cutoff']}; {len(frame)} SPY bars")
    if args.command == "prepare":
        return
    if args.command == "research":
        selection = select(frame, args.output, args.phase)
    else:
        selection = json.loads(args.config.read_text())
    report, results = evaluate(frame, selection, metadata)
    common = sources["SPY"].Close.pct_change(fill_method=None).rename("spy").to_frame().join(
        sources["QQQ"].Close.pct_change(fill_method=None).rename("qqq")).loc[:"2009-12-31"].dropna()
    report["training_asset_comparison"] = {
        "spy_beta_to_qqq": float(common.spy.cov(common.qqq) / common.qqq.var()),
        "spy_to_qqq_volatility_ratio": float(common.spy.std() / common.qqq.std()),
        "start": str(common.index[0].date()), "end": str(common.index[-1].date())}
    write_outputs(report, results, args.output)
    print_results(report, args.output)


if __name__ == "__main__":
    main()
