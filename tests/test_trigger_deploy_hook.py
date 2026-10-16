import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scripts.trigger_deploy_hook import NoRedirects, trigger_build


HOOK = "https://api.cloudflare.com/client/v4/workers/builds/deploy_hooks/private-hook"


class DeployHookTests(unittest.TestCase):
    def test_posts_once_and_accepts_new_or_already_queued_build(self):
        for existing in [False, True]:
            with self.subTest(existing=existing), patch("scripts.trigger_deploy_hook.build_opener") as opener:
                opener.return_value.open.return_value = io.BytesIO(json.dumps({
                    "success": True, "result": {"build_uuid": "build-123", "already_exists": existing},
                }).encode())
                self.assertEqual(trigger_build(HOOK), "build-123")
                opener.return_value.open.assert_called_once()
                request = opener.return_value.open.call_args.args[0]
                self.assertEqual(request.get_method(), "POST")
                self.assertEqual(request.full_url, HOOK)
                self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 20)

    def test_missing_or_wrong_hook_is_rejected_before_network(self):
        for invalid in ["", "https://example.com/hook", HOOK.replace("https:", "http:"),
                        HOOK + "?token=secret", HOOK + "#fragment", HOOK.replace("api.cloudflare.com", "api.cloudflare.com@evil.example")]:
            with self.subTest(invalid=invalid), patch("scripts.trigger_deploy_hook.build_opener") as opener:
                with self.assertRaises(ValueError):
                    trigger_build(invalid)
                opener.assert_not_called()

    def test_network_errors_never_include_the_secret(self):
        for error in [URLError(HOOK), HTTPError(HOOK, 403, HOOK, {}, None)]:
            with self.subTest(error=type(error).__name__), patch("scripts.trigger_deploy_hook.build_opener") as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaises(RuntimeError) as caught:
                    trigger_build(HOOK)
                self.assertNotIn("private-hook", str(caught.exception))
                opener.return_value.open.assert_called_once()

    def test_unconfirmed_builds_and_invalid_json_fail(self):
        for payload in [b"<html>Error</html>", b"[]", b"null", b'{"success":false}',
                        b'{"success":true,"result":{}}', b'{"success":true,"result":{"build_uuid":""}}']:
            with self.subTest(payload=payload), patch("scripts.trigger_deploy_hook.build_opener") as opener:
                opener.return_value.open.return_value = io.BytesIO(payload)
                with self.assertRaises(RuntimeError):
                    trigger_build(HOOK)

    def test_redirects_are_not_followed(self):
        self.assertIsNone(NoRedirects().redirect_request(None, None, 302, "", {}, "https://example.com"))


if __name__ == "__main__":
    unittest.main()
