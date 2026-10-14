# Cloudflare Automatic Updates: Worker + Wrangler + Workers Builds

One Worker serves the static report and uses Cron to call its own Workers Builds Deploy Hook. The build environment runs the existing Python pipeline, then Wrangler publishes `dist/` and the Worker together.

```text
06:30 Beijing time, Tuesday through Saturday
  → Worker Cron → Workers Builds Hook
  → Fetch Git repository → Download prices → Backtest → Generate dist/
  → Wrangler publishes this Worker and its static report
```

Root `wrangler.jsonc` binds `dist/` and configures the Worker code. `package.json` / `package-lock.json` pin Wrangler; Worker source is `cloudflare/worker.mjs`. The user manages the production domain, workers.dev, Preview URLs and Cron in the Cloudflare dashboard. The repository omits `workers_dev`, `preview_urls` and `triggers`.

## 1. Connect Workers Builds

Commit and push configuration changes first. Do not commit `prices.csv`, `results.json`, `report_data.js`, `dist/` or `node_modules/`.

In Cloudflare **Workers & Pages**, create a Worker and import `smilekevin/QQQ-rolling-Strategy`, or connect that repository to an existing Worker. If the repository is missing, open [GitHub installed applications](https://github.com/settings/installations), configure Cloudflare Workers and Pages repository access and authorize this repository.

| Setting | Value |
|---|---|
| Worker name | `qqq-strategy-auto-deploy`, matching `name` in `wrangler.jsonc` |
| Production branch | `main` |
| Root directory | Repository root; leave blank or use the default |
| Build command | `bash build_cloudflare.sh` |
| Deploy command | `npm run deploy` |
| Preview command | `npm run preview` |
| Build environment variable `PYTHON_VERSION` | `3.12.10` |

**Workers Builds does not need a Build output directory:** `dist/` is already configured in Wrangler’s `assets.directory`. If the connected Worker has another name, change the configuration’s `name`, commit and push.

The build installs Python dependencies and validates the SQLite read/write backend required by yfinance caching. It then runs `1 → 2 → 3` in a temporary directory. After current-price, date and series checks pass, it produces the home page, original report HTML, `report_data.js` and `_headers`. Downloads/price validation allow three attempts. Failed builds do not publish a new version.

After a successful build, open production at [qqq-strategy.kenzhu.link](https://qqq-strategy.kenzhu.link) and verify the latest trading date. The user has already bound this custom domain. Disable the default production workers.dev address and enable Preview URL in the dashboard if desired; existing custom-domain bindings remain managed there. Assets have priority, and `_headers` requires revalidation of `report_data.js`. Page visits only read the report and never trigger builds.

`npm run deploy` remains `wrangler deploy`. Omitting `preview_urls` preserves the dashboard’s preview switch; omitting `triggers` / `crons` preserves existing schedules. **workers.dev has a different default:** without `workers_dev` or repository routes, production deployment may re-enable the default workers.dev address. The user accepts this, and it can coexist with the custom domain. Pinned Wrangler 4.150.0 does not explicitly disable an existing preview route when `preview_urls` is omitted. See [workers.dev defaults](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/), [Preview URL settings](https://developers.cloudflare.com/workers/previews/custom-domains/) and [Cron preservation](https://developers.cloudflare.com/workers/configuration/cron-triggers/#remove-a-cron-trigger).

### Preview feature branches; the user merges in the PR

Start each change from latest `main` on a purpose-named branch, such as `feat/cloudflare-preview`, `feat/...` or `fix/...`. Commit, push and create a PR to `main`. The branch need not be named `preview`.

In **this Worker → Settings → Builds → Branch control**, keep `main` as production and enable **Enable Preview Builds**. Set **Preview command** to `npm run preview`; keep Build command `bash build_cloudflare.sh` and production Deploy command `npm run deploy`. Pushes to non-production branches then trigger independent preview builds.

If the existing Worker displays **Set up Worker Previews**, follow the dashboard migration before using that Preview command. Pinned Wrangler 4.150.0 supports it. This one-time migration cannot be reversed; see [branch builds](https://developers.cloudflare.com/workers/ci-cd/builds/build-branches/).

In `npm run preview`, `preview` is an npm script name, not a Git branch. Wrangler creates or updates a separate preview for the current build’s branch without publishing production. Root `previews: {}` is configured and assets come from that build’s `dist/`. Preview routing is managed in the dashboard; version and branch URLs require it to be enabled. **Do not add the production `DEPLOY_HOOK_URL` Secret to Previews Base.** Cron and the daily Hook continue to target production `main`.

**Initial preview enablement:** turn on Preview URL at **Domains → Worker URL → Preview**, or **Settings → Domains & Routes → Preview URLs / Version URLs**, depending on the interface. `wrangler preview` creates a branch preview but does not synchronize production domain-routing settings. A successful build and a bot-posted URL may therefore still return `404 / error code: 1042` if routing is disabled. Omitted `preview_urls` preserves current state; it does not disable an enabled route, but an initially disabled route still needs manual enablement. See [Worker Previews domains](https://developers.cloudflare.com/workers/previews/custom-domains/).

Confirm the build for **the feature branch’s exact commit** in Builds or PR checks, open its Preview URL, and verify the latest trading date, home page, charts and data loading. For the bilingual report, check first-visit English/Chinese detection, the top-right language switch and remembered preferences. **The user merges manually in GitHub.** Codex commits, pushes and opens PRs, without merging or pushing directly to `main`. Keep changes on the feature branch when only local checks pass, the remote build is still running, or a build fails. Merging to `main` triggers a fresh production build/deployment.

**Pull request comment:** create a `feature branch → main` PR. With the repository connected through the Cloudflare Workers & Pages GitHub App, builds on PR commits automatically post status comments; `wrangler preview` builds also include Preview URLs. Later pushes update the same branch preview. After enabling preview builds and creating the PR, push a change or manually trigger that branch’s build in Cloudflare. A branch without a PR does not receive PR comments. See [GitHub integration](https://developers.cloudflare.com/workers/ci-cd/builds/git-integration/github-integration/).

From a clean workspace, create a branch from latest `main` and commit. The following branch is an example; choose a name for each task:

```bash
git fetch origin
git switch --no-track -c feat/cloudflare-preview origin/main
# Edit files, then explicitly stage the files for this task
git add <files-for-this-change>
git commit -m "Describe this change"
git push -u origin feat/cloudflare-preview
```

Create the GitHub PR with **base = `main`, compare = the current feature branch**. Once build checks and page validation pass, the user clicks Merge in the PR.

If updated `main` causes conflicts, resolve them on the feature branch, push and revalidate its latest commit before handing it back for merging. Pushes before preview enablement may not have triggered a build; start one manually for that branch in Cloudflare Builds.

## 2. Create this Worker’s Deploy Hook

In **the same Worker → Settings → Builds → Deploy Hooks**, create a Hook named, for example, `daily-market-update`, select `main` and copy the generated URL:

```text
https://api.cloudflare.com/client/v4/workers/builds/deploy_hooks/<HOOK_ID>
```

In **Settings → Variables and Secrets**, add `DEPLOY_HOOK_URL` as a **Secret** with that URL, save and deploy. This is a runtime Secret, not a build environment variable.

When migrating from Pages, replace the existing Secret with this Worker’s Workers Builds Hook. The Worker validates the URL format before sending and checks for a build ID in the API response. The old Pages Hook is incompatible with this setup.

## 3. Configure the schedule in the dashboard

In **Settings → Triggers → Cron Triggers**, add `30 22 * * MON-FRI`. Change or pause the schedule there. The repository omits `triggers`, so Wrangler preserves existing schedules. Never set `crons: []`: an empty array removes every Cron trigger.

Cloudflare Cron uses UTC. This expression is **06:30 Beijing time Tuesday–Saturday**, corresponding to 18:30 New York daylight time or 17:30 standard time. Changes may take up to 15 minutes to apply.

The build rejects same-day daily bars before 17:00 New York time and prices more than seven calendar days old. This is a permissive staleness check, without an exchange holiday calendar, and does not guarantee every source instrument has updated. Existing download filling is unchanged. US holidays may publish the same trading date again.

## 4. Local Wrangler usage

Use Node.js and a Python environment with `requirements.txt` installed. From the repository root:

```bash
npm ci
source .venv/bin/activate
npm run build
npx wrangler login
npm run preview
```

If needed, create the virtual environment with `python3 -m venv .venv`. On the current feature branch, these commands generate a report and publish its branch preview. Production is published by Workers Builds after the user merges the PR to `main`; `npm run deploy` is the production command. Full automation still requires Steps 1–3: Workers Builds, the Hook and dashboard Cron.

Set or replace the runtime Secret:

```bash
npx wrangler secret put DEPLOY_HOOK_URL
```

Preview locally or check packaging only:

```bash
npm run dev
npm run check:deploy
```

## 5. Verification and troubleshooting

- Confirm the first Workers Builds build and deployment succeed and the site displays the latest trading date.
- After the next scheduled trigger, Worker Logs should show that Workers Builds was triggered and include its build ID. Confirm that build succeeds in Builds. A successful Hook request means only that a build was created.
- Missing Git repository: check GitHub App repository permissions and the selected GitHub account in Cloudflare.
- Worker name mismatch: align Wrangler `name` with the Worker connected to Workers Builds.
- Hook error: confirm `DEPLOY_HOOK_URL` belongs to this Worker’s Builds and targets `main`.
- `SQLite driver not installed!`: some Cloudflare Python builds lack standard-library `_sqlite3`. `requirements.txt` pins `pysqlite3-binary` on Linux x86_64; Peewee uses it automatically. Logs should show successful runtime validation and a driver name before downloads start. Rebuild after updating to the fix commit; no Worker-setting change or pip upgrade is needed.
- Worker succeeds but the site is stale: inspect Python download, backtest and deployment logs in Builds.
- Successful preview build but `404 / error code: 1042`: confirm Preview URL routing is enabled in the dashboard. Open the preview home page and `report_data.js`; build status alone is insufficient.

Read-only live logs: `npx wrangler tail`. Pause automatic updates by removing or disabling this Worker’s Cron trigger in the dashboard.

Official documentation: [Workers Builds configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/), [branch builds](https://developers.cloudflare.com/workers/ci-cd/builds/build-branches/), [Worker Previews configuration](https://developers.cloudflare.com/workers/previews/configuration/), [Python build environment](https://developers.cloudflare.com/workers/ci-cd/builds/build-image/), [Workers Builds Deploy Hooks](https://developers.cloudflare.com/workers/ci-cd/builds/deploy-hooks/), [static assets](https://developers.cloudflare.com/workers/static-assets/binding/) and [static cache headers](https://developers.cloudflare.com/workers/static-assets/headers/).
