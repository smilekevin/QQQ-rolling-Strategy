import assert from "node:assert/strict";
import test from "node:test";
import worker from "../cloudflare/worker.mjs";

test("HTTP requests still use the static asset binding", async () => {
  const request = new Request("https://example.com/report_data.js");
  const response = new Response("report");
  const result = await worker.fetch(request, {
    ASSETS: { fetch: async (actual) => { assert.equal(actual, request); return response; } },
  });
  assert.equal(result, response);
});

test("an old dashboard Cron never requires credentials or calls a Hook", async (t) => {
  const outbound = t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected outbound request"); });
  const log = t.mock.method(console, "warn", () => {});
  await worker.scheduled({ scheduledTime: Date.parse("2026-10-15T22:30:00Z") }, {});
  assert.equal(outbound.mock.callCount(), 0);
  assert.match(log.mock.calls[0].arguments[0], /GitHub Actions/);
});
