"""Request a Workers Builds deployment without exposing the Hook URL in logs."""
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def trigger_build(hook_url):
    if not hook_url:
        raise ValueError("Add DEPLOY_HOOK_URL to GitHub repository Actions secrets.")
    try:
        parts = urlsplit(hook_url)
        valid = (
            parts.scheme == "https" and parts.netloc == "api.cloudflare.com"
            and re.fullmatch(r"/client/v4/workers/builds/deploy_hooks/[A-Za-z0-9_-]+", parts.path)
            and not parts.query and not parts.fragment
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("DEPLOY_HOOK_URL must be this Worker's Workers Builds Deploy Hook for main.")

    request = Request(hook_url, method="POST")
    try:
        with build_opener(NoRedirects()).open(request, timeout=20) as response:
            data = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"Deploy Hook returned HTTP {error.code}; check the Hook in Cloudflare.") from None
    except (URLError, OSError, ValueError):
        raise RuntimeError("Deploy Hook request failed, timed out or returned invalid JSON.") from None

    result = data.get("result") if isinstance(data, dict) else None
    build_id = result.get("build_uuid") if isinstance(result, dict) else None
    if not isinstance(data, dict) or data.get("success") is not True or not isinstance(build_id, str) or not re.fullmatch(r"[A-Za-z0-9-]+", build_id):
        raise RuntimeError("Cloudflare did not confirm a build ID; check the Hook configuration.")
    return build_id


def main():
    try:
        build_id = trigger_build(os.environ.get("DEPLOY_HOOK_URL", ""))
    except (ValueError, RuntimeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    message = f"Cloudflare accepted build {build_id}. Check Workers Builds for deployment results; this workflow does not wait for deployment."
    print(message)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as output:
            output.write(message + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
