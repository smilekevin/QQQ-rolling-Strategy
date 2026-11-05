"""Publishing contracts for the two strategy pages."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_report


class BuildReportsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.spy = self.work / "spy"
        self.spy.mkdir()
        (self.spy / "spy_report.html").write_text('<html lang="en">SPY report</html>')
        self.cutoff = "2026-11-04"
        self.report = {"data": {"cutoff": self.cutoff},
                       "latest": {"date": self.cutoff},
                       "metrics": {"strategy": {"full": {"end": self.cutoff}}}}

    def write_report(self):
        (self.spy / "results.json").write_text(json.dumps(self.report))

    def test_build_refreshes_frozen_strategy_at_qqq_cutoff_in_isolated_directory(self):
        self.write_report()
        with patch.object(build_report.subprocess, "run") as run:
            page = build_report.build_spy_report(self.work, self.cutoff)
        command = run.call_args.args[0]
        self.assertEqual(command[1:6], ["-m", "spy_strategy", "backtest", "--refresh", "--as-of"])
        self.assertEqual(command[6:], [self.cutoff, "--output", str(self.spy)])
        self.assertEqual(run.call_args.kwargs, {"cwd": build_report.ROOT, "check": True})
        self.assertEqual(page, self.spy / "spy_report.html")

    def test_any_mismatched_report_date_prevents_publishing(self):
        for field in ("data", "latest", "metrics"):
            with self.subTest(field=field):
                self.reset_report_dates()
                if field == "data":
                    self.report["data"]["cutoff"] = "2026-11-03"
                elif field == "latest":
                    self.report["latest"]["date"] = "2026-11-03"
                else:
                    self.report["metrics"]["strategy"]["full"]["end"] = "2026-11-03"
                self.write_report()
                with patch.object(build_report.subprocess, "run"):
                    with self.assertRaisesRegex(ValueError, "same validated cutoff"):
                        build_report.build_spy_report(self.work, self.cutoff)

    def reset_report_dates(self):
        self.report = {"data": {"cutoff": self.cutoff}, "latest": {"date": self.cutoff},
                       "metrics": {"strategy": {"full": {"end": self.cutoff}}}}

    def test_unrendered_template_is_not_published(self):
        self.write_report()
        (self.spy / "spy_report.html").write_text("<html>const R=/* REPORT_DATA */;</html>")
        with patch.object(build_report.subprocess, "run"):
            with self.assertRaisesRegex(ValueError, "no generated data"):
                build_report.build_spy_report(self.work, self.cutoff)

    def test_only_static_assets_are_published_with_original_qqq_shell(self):
        shell = "<html>QQQ original</html>"
        (self.root / "qqq_qld_report.html").write_text(shell)
        (self.root / "_headers").write_text("/spy\n  Cache-Control: no-cache\n")
        (self.work / "report_data.js").write_text("window.QQQ_REPORT_DATA = {};")
        (self.spy / "prices.csv").write_text("private build cache")
        destination = self.root / "dist"
        with patch.object(build_report, "ROOT", self.root):
            build_report.publish_assets(self.work, self.spy / "spy_report.html", destination)
        self.assertEqual({p.name for p in destination.iterdir()},
                         {"index.html", "qqq_qld_report.html", "report_data.js", "spy.html", "_headers"})
        self.assertEqual((destination / "index.html").read_text(), shell)
        self.assertEqual((destination / "spy.html").read_text(), '<html lang="en">SPY report</html>')


if __name__ == "__main__":
    unittest.main()
