"""Verify that production serves the report built by this workflow run."""
import argparse
import json
import os
from pathlib import Path
import time
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REPORT_URL = "https://qqq-strategy.kenzhu.link/report_data.js"
PREFIX = "window.QQQ_REPORT_DATA = "


def parse_report(payload):
    text = payload.strip()
    if not text.startswith(PREFIX) or not text.endswith(";"):
        raise ValueError("Response is not a report_data.js payload")
    report = json.loads(text[len(PREFIX):-1])
    if not isinstance(report, dict) or not report.get("latest", {}).get("date"):
        raise ValueError("Report has no latest trading date")
    return report


def verify_deployment(expected_path, url=REPORT_URL, attempts=6, delay=10):
    expected = parse_report(Path(expected_path).read_text(encoding="utf-8"))
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError("Deployment verification requires an HTTPS URL")
    for attempt in range(attempts):
        query = parse_qsl(parts.query, keep_blank_values=True)
        query.append(("deployment_check", str(time.time_ns())))
        fresh_url = urlunsplit(parts._replace(query=urlencode(query)))
        request = Request(fresh_url, headers={
            "Cache-Control": "no-cache", "User-Agent": "QQQStrategy-deployment-check",
        })
        try:
            with urlopen(request, timeout=20) as response:
                actual = parse_report(response.read().decode("utf-8"))
            if actual != expected:
                raise ValueError("Published report does not match this build")
            return expected["latest"]["date"]
        except (URLError, OSError, ValueError) as error:
            if attempt == attempts - 1:
                raise RuntimeError("Deployment verification failed") from error
            print(f"Published report not ready ({attempt + 1}/{attempts}); retrying", flush=True)
            time.sleep(delay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=Path, default=ROOT / "dist" / "report_data.js")
    parser.add_argument("--url", default=REPORT_URL)
    args = parser.parse_args()
    date = verify_deployment(args.expected, args.url)
    message = f"Verified production report: {date} ({args.url})"
    print(message)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"{message}\n")


if __name__ == "__main__":
    main()
