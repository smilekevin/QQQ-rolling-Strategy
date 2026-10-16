// Workers Assets serves the report; GitHub Actions owns scheduled updates.
export default {
  async fetch(request, env) {
    // Existing files are served first; unmatched requests use the ASSETS 404 behavior.
    return env.ASSETS.fetch(request);
  },

  async scheduled(controller) {
    // A dashboard Cron may remain during migration. Never call the old Hook.
    console.warn("Legacy Cloudflare Cron ignored: daily updates now run in GitHub Actions. Remove this Cron in the dashboard.", {
      scheduledTime: new Date(controller.scheduledTime).toISOString(),
    });
  },
};
