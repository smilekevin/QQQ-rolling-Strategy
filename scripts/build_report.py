"""Build date-aligned QQQ and SPY reports, then publish only static assets."""
import csv
from datetime import date, datetime
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

# Also support direct execution as `python scripts/build_report.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from market_sessions import latest_completed_session


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "1_prepare_data.py", "2_backtest.py", "3_generate_report.py",
    "indicators.py", "execution.py", "market_sessions.py",
)


def validate_prices(path):
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError("下载结果为空")
    latest = rows[-1]
    market_now = datetime.now(ZoneInfo("America/New_York"))
    latest_date = date.fromisoformat(latest["Date"])
    if latest_date > market_now.date():
        raise ValueError("行情日期晚于纽约当前日期")
    expected_date = latest_completed_session(market_now)
    if latest_date > expected_date:
        raise ValueError("行情尚未到该交易日收盘后一小时的校验时间（常规交易日 17:00 ET）")
    if latest_date < expected_date:
        raise ValueError(f"最新完整交易日应为 {expected_date}，实际行情仅到 {latest_date}；拒绝发布旧数据")
    for column in (
        "signal_close", "signal_high", "signal_low", "qqq", "qopen",
        "qhigh", "qlow", "qld", "qld_open", "vix",
    ):
        try:
            value = float(latest[column])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"最新行情 {latest_date} 的 {column} 缺失或无效") from error
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"最新行情 {latest_date} 的 {column} 缺失或无效")
    return latest["Date"]


def validate_report(path, latest_date):
    with path.open(encoding="utf-8") as source:
        report = json.load(source)
    dates = report["dates"]
    if not dates or dates[-1] != latest_date or report["latest"]["date"] != latest_date:
        raise ValueError("回测曲线、最新信号与行情日期不一致")
    for name, values in report["equity"].items():
        if len(values) != len(dates) or any(
            not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0
            for value in values
        ):
            raise ValueError(f"净值序列 {name} 缺失或无效")
    for name in ("state_exp", "decision"):
        if len(report[name]) != len(dates):
            raise ValueError(f"报告序列 {name} 与日期长度不一致")


def build_spy_report(work, latest_date):
    """Refresh the frozen SPY strategy at the validated QQQ cutoff, never retune."""
    output = work / "spy"
    subprocess.run(
        [sys.executable, "-m", "spy_strategy", "backtest", "--refresh",
         "--as-of", latest_date, "--output", str(output)],
        cwd=ROOT, check=True,
    )
    with (output / "results.json").open(encoding="utf-8") as source:
        report = json.load(source)
    if any(value != latest_date for value in (
        report["data"]["cutoff"], report["latest"]["date"],
        report["metrics"]["strategy"]["full"]["end"],
    )):
        raise ValueError("SPY report and QQQ report must have the same validated cutoff")
    page = output / "spy_report.html"
    html = page.read_text(encoding="utf-8")
    if "<html" not in html or "/* REPORT_DATA */" in html:
        raise ValueError("SPY report HTML is missing or has no generated data")
    return page


def publish_assets(work, spy_page, dist):
    """Flat spy.html is served at /spy by Workers Assets HTML handling."""
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()
    shutil.copy2(ROOT / "qqq_qld_report.html", dist / "index.html")
    shutil.copy2(ROOT / "qqq_qld_report.html", dist / "qqq_qld_report.html")
    shutil.copy2(ROOT / "_headers", dist / "_headers")
    shutil.copy2(work / "report_data.js", dist / "report_data.js")
    shutil.copy2(spy_page, dist / "spy.html")


def main():
    with tempfile.TemporaryDirectory(prefix="qqq-report-") as temporary:
        work = Path(temporary)
        for name in SOURCES:
            shutil.copy2(ROOT / name, work / name)
        # 每次重新下载；不会读取本地 gitignored 的旧数据或覆盖本地研究产物。
        for attempt in range(1, 4):
            try:
                subprocess.run([sys.executable, str(work / SOURCES[0])], check=True)
                latest_date = validate_prices(work / "prices.csv")
                break
            except (subprocess.CalledProcessError, ValueError) as error:
                if attempt == 3:
                    raise
                print(f"下载/校验失败，第 {attempt}/3 次：{error}；10 秒后重试", flush=True)
                time.sleep(10)
        for name in SOURCES[1:3]:
            subprocess.run([sys.executable, str(work / name)], check=True)
        validate_report(work / "results.json", latest_date)
        # Complete both builds before replacing any previously generated assets.
        spy_page = build_spy_report(work, latest_date)
        dist = ROOT / "dist"
        publish_assets(work, spy_page, dist)
        print(f"Cloudflare QQQ (/) and SPY (/spy) reports: {dist}; cutoff: {latest_date}",
              flush=True)


if __name__ == "__main__":
    main()
