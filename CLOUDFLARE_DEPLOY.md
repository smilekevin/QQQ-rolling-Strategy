# Cloudflare Hosting with GitHub Actions Scheduled Hooks

Cloudflare downloads prices, runs the Python pipeline and deploys the report. GitHub Actions only sends a scheduled or manual POST request to a Workers Builds Deploy Hook. All build and deployment logs remain in Cloudflare.

```text
06:30 Beijing time, Tuesday through Saturday
  → GitHub Actions schedule (UTC Monday-Friday 22:30)
  → POST the main-branch Deploy Hook
  → Cloudflare downloads prices → Backtests → Generates dist/ → Wrangler deploy
```

Workflow: [`.github/workflows/update-report.yml`](./.github/workflows/update-report.yml). The strategy, bilingual page, report-data format, temporary-directory build and current price/series checks are unchanged.

## 1. Configure one GitHub repository secret

Open **Cloudflare → Workers & Pages → qqq-strategy-auto-deploy → Settings → Builds → Deploy Hooks**. Create a Hook named, for example, `github-daily-report`, select branch **main** and copy its URL. An existing Workers Builds Hook targeting this Worker and `main` can be reused. A Pages Hook is not compatible. See [Cloudflare Deploy Hooks](https://developers.cloudflare.com/workers/ci-cd/builds/deploy-hooks/).

In the GitHub repository, open **Settings → Secrets and variables → Actions → Repository secrets → New repository secret** and add:

| Secret | Value |
|---|---|
| `DEPLOY_HOOK_URL` | This Worker's Workers Builds Deploy Hook URL targeting `main` |

Store the URL in GitHub Actions secrets, rather than Worker runtime or Cloudflare Builds variables. The Hook URL authenticates the request; no `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` or Authorization header is required. Do not commit or print the URL. Worker deployments cannot overwrite this GitHub Secret.

## 2. Merge the PR, then trigger once manually

1. Review the feature branch's checks and Cloudflare preview. The user merges the PR into `main`.
2. Open **GitHub → Actions → Trigger Cloudflare report build → Run workflow** and choose **main**.
3. Actions prints the accepted Cloudflare build ID. Open this Worker's **Builds** history, find the corresponding Deploy Hook build and inspect its build/deploy logs.
4. Wait for Cloudflare to report deployment success, then open [qqq-strategy.kenzhu.link](https://qqq-strategy.kenzhu.link) and confirm the latest trading date and charts.

**A successful Actions run means Cloudflare accepted a build request; it does not mean deployment completed or succeeded.** The workflow does not poll deployment status or verify the published report. Cloudflare Builds is the source for final results. A repeated request while a build is queued/initializing may return that same build ID.

[`scripts/trigger_deploy_hook.py`](./scripts/trigger_deploy_hook.py) validates the Workers Builds URL, sends one POST with a 20-second timeout and rejects redirects, HTTP/network errors, invalid JSON or a response without success and a build ID. Error messages omit the secret URL. There are no automatic POST retries; inspect Cloudflare before manually retrying an uncertain request.

Scheduled/manual requests run only from `main`; choosing a feature branch skips the job. PR checks install Python test dependencies and run strategy-consistency, mocked Hook and Worker tests without accessing the Secret or triggering production. Cloudflare continues building branch previews. The scheduled/manual job does not install dependencies; no GitHub job builds assets, runs Wrangler, pushes generated data or merges PRs. Concurrent production workflow runs are serialized.

Cloudflare retains the existing `bash build_cloudflare.sh` pipeline: dependency installation, SQLite validation, price downloads with up to three attempts, temporary-directory backtest/report generation and four assets in `dist/`, followed by `npm run deploy`.

## 3. Retire the old Worker Cron

After a successful manual Hook request **and Cloudflare deployment**:

- Open **Cloudflare → Workers & Pages → qqq-strategy-auto-deploy → Settings → Triggers / Trigger Events** and remove the old `30 22 * * MON-FRI` Cron.
- Remove unused `DEPLOY_HOOK_URL` entries from Worker runtime variables/secrets and build variables. Keep the Deploy Hook whose URL is now stored in GitHub.
- Leave the custom domain, Preview URL settings and Workers Builds Git connection in place. Previously configured GitHub `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` secrets are not used by this workflow and may be removed if unused elsewhere.

For migration, `cloudflare/worker.mjs` retains a no-op `scheduled()` handler. An old dashboard Cron only logs that scheduling moved to GitHub Actions; it never calls a Hook or starts another build. A successful legacy Cron event does not mean a report update ran.

Root `wrangler.jsonc` still omits `workers_dev`, `preview_urls` and `triggers`. The repository does not delete dashboard Cron settings automatically. Domain and preview routing remain managed by the user in Cloudflare.

## 4. Schedule and recovery

The workflow expression is `30 22 * * 1-5` in UTC: **06:30 Beijing time Tuesday–Saturday**, corresponding to 18:30 New York daylight time or 17:30 standard time. Edit the workflow through the normal branch/PR process to change this time. Disable the workflow in GitHub Actions to pause daily updates, or use **Run workflow → main** to recover a missed run.

GitHub schedules run only from the default branch, which must remain `main`; the workflow must be merged there before the schedule becomes active. Scheduled starts can be delayed or, under sufficiently high load, dropped. Public-repository schedules are disabled after 60 days without repository activity; re-enable them in Actions if this happens. The schedule is not an exact-time guarantee. See [GitHub scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

The existing build rejects same-day daily bars before 17:00 New York time and prices more than seven calendar days old. This is a permissive staleness check, not an exchange calendar or proof every source instrument has updated. US holidays may publish the same trading date. The original filling and execution methodology is unchanged.

## 5. Keep Cloudflare push deployments and PR previews

The GitHub schedule complements the existing Cloudflare Git integration. Cloudflare Workers Builds continues deploying production after a user merges into `main`, and building separate previews for non-production branches:

| Cloudflare Workers Builds setting | Value |
|---|---|
| Worker name | `qqq-strategy-auto-deploy`, matching `wrangler.jsonc` |
| Production branch | `main` |
| Root directory | Repository root |
| Build command | `bash build_cloudflare.sh` |
| Deploy command | `npm run deploy` |
| Preview command | `npm run preview` |
| Build environment variable `PYTHON_VERSION` | `3.12.10` |

No Build output directory is needed; Wrangler already binds `dist/`. If GitHub repositories are missing in Cloudflare, configure repository access for the Cloudflare Workers and Pages app at [GitHub installed applications](https://github.com/settings/installations).

Enable **Settings → Builds → Branch control → Enable Preview Builds**. If the dashboard first requests **Set up Worker Previews**, complete that one-time migration; it cannot be reversed. Pinned Wrangler 4.150.0 supports `wrangler preview`. See [branch builds](https://developers.cloudflare.com/workers/ci-cd/builds/build-branches/).

Root `previews: {}` uses the current branch’s assets. Preview routing must be enabled in **Domains → Worker URL → Preview** or **Settings → Domains & Routes → Preview URLs / Version URLs**. A successful build can still return `404 / error code: 1042` if this routing is disabled. See [Worker Previews domains](https://developers.cloudflare.com/workers/previews/custom-domains/).

The Cloudflare GitHub App continues posting build status and Preview URLs on PRs. Check the exact commit’s build, open its preview and `report_data.js`, verify the date/charts and test both report languages. Only the user merges PRs. Feature branches need not be called `preview`; create a purpose-named branch from latest `main` for each task. See [GitHub integration](https://developers.cloudflare.com/workers/ci-cd/builds/git-integration/github-integration/).

Wrangler preserves existing preview and Cron settings when their fields are omitted. workers.dev may default to enabled when omitted without repository routes; the user accepts this. Ordinary runtime variables added in the dashboard can be replaced by deployment unless `keep_vars` is enabled, while encrypted Secrets are preserved. Daily updates no longer depend on either kind of runtime credential. See [Wrangler configuration behavior](https://developers.cloudflare.com/workers/wrangler/configuration/#source-of-truth).

## 6. Local usage and troubleshooting

Use Node.js and a Python environment with `requirements.txt` installed:

```bash
npm ci
source .venv/bin/activate
npm run build
npm run check:deploy
npx wrangler login
npm run preview
```

Create a missing virtual environment with `python3 -m venv .venv`. `npm run preview` publishes the current feature branch’s preview. Production is published by Cloudflare on merges or scheduled/manual Deploy Hook requests; do not publish an unmerged feature branch to production. `npm run dev` previews locally.

Local regression checks:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/worker.test.mjs
```

Troubleshooting:

- **Missing Hook:** add `DEPLOY_HOOK_URL` to GitHub repository Actions secrets. Names are case-sensitive. Cloudflare runtime/build variables do not provide GitHub secrets.
- **No scheduled run:** check that the workflow is on default `main`, Actions is enabled and the workflow is not disabled. Inspect GitHub Actions rather than Cloudflare Cron events.
- **Hook request failure:** confirm the URL belongs to this Worker and targets `main`. Recreate a deleted Hook and replace the GitHub Secret. No API token or Authorization header is required.
- **`SQLite driver not installed!`:** Linux x86_64 installs pinned `pysqlite3-binary`; the existing runtime check must succeed before downloads. This compatibility fallback is retained for Cloudflare Builds too.
- **Download/backtest/deployment failure:** inspect Cloudflare Workers Builds logs using the build ID from Actions. Fix the cause and run the GitHub workflow again on `main`.
- **Actions succeeded but the page is old:** Actions only confirms the build request was accepted. Check that the matching Cloudflare build completed successfully, then check the production report date and routing/cache.
- **Preview 404/1042:** enable Preview URL routing in Cloudflare, then verify the actual page and report data.
