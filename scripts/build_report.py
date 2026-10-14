"""在临时目录运行原流水线，检查后只将静态报告复制到 dist。"""
import csv
from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "1_prepare_data.py", "2_backtest.py", "3_generate_report.py",
    "indicators.py", "execution.py",
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
    # 常规交易 16:00 ET 收盘后至少等一小时；兼容北京时间 06:30 的全年调度。
    if latest_date == market_now.date() and market_now.hour < 17:
        raise ValueError("当日日线尚未到盘后校验时间；请在纽约时间 17:00 后构建")
    # 允许周末、节假日；这是宽松的过期检查，不替代交易所日历。
    if latest_date < market_now.date() - timedelta(days=7):
        raise ValueError(f"行情已超过 7 个自然日未更新：{latest_date}")
    for column in (
        "signal_close", "signal_high", "signal_low", "qqq", "qopen",
        "qhigh", "qlow", "qld", "qld_open", "vix",
    ):
        value = float(latest[column])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"最新行情 {column} 缺失或无效")
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
        dist = ROOT / "dist"
        if dist.exists():
            shutil.rmtree(dist)
        dist.mkdir()
        shutil.copy2(ROOT / "qqq_qld_report.html", dist / "index.html")
        shutil.copy2(ROOT / "qqq_qld_report.html", dist / "qqq_qld_report.html")
        shutil.copy2(ROOT / "_headers", dist / "_headers")
        shutil.copy2(work / "report_data.js", dist / "report_data.js")
        print(f"Cloudflare 静态报告已生成：{dist}；行情日期：{latest_date}", flush=True)


if __name__ == "__main__":
    main()
