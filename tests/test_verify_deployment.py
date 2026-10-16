import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from scripts.verify_deployment import parse_report, verify_deployment


def payload(value):
    return "window.QQQ_REPORT_DATA = " + json.dumps(value) + ";\n"


class DeploymentVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.expected = Path(self.temporary.name) / "report_data.js"
        self.report = {"latest": {"date": "2026-10-15"}, "equity": {"strategy": [1, 1.1]}}
        self.expected.write_text(payload(self.report), encoding="utf-8")

    def test_matches_full_report_and_bypasses_cache(self):
        with patch("scripts.verify_deployment.urlopen", return_value=io.BytesIO(payload(self.report).encode())) as fetch:
            self.assertEqual(verify_deployment(self.expected), "2026-10-15")
        request = fetch.call_args.args[0]
        self.assertIn("deployment_check=", request.full_url)
        self.assertEqual(request.get_header("Cache-control"), "no-cache")

    def test_same_date_but_stale_values_fail(self):
        stale = {**self.report, "equity": {"strategy": [1, 1.05]}}
        with patch("scripts.verify_deployment.urlopen", return_value=io.BytesIO(payload(stale).encode())):
            with self.assertRaisesRegex(RuntimeError, "verification failed"):
                verify_deployment(self.expected, attempts=1)

    def test_retries_network_failure_then_succeeds(self):
        with patch("scripts.verify_deployment.urlopen", side_effect=[URLError("unavailable"), io.BytesIO(payload(self.report).encode())]) as fetch:
            self.assertEqual(verify_deployment(self.expected, attempts=2, delay=0), "2026-10-15")
            self.assertEqual(fetch.call_count, 2)

    def test_html_error_page_and_missing_date_are_rejected(self):
        for invalid in ["<html>Not found</html>", payload({"latest": {}})]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_report(invalid)


if __name__ == "__main__":
    unittest.main()
