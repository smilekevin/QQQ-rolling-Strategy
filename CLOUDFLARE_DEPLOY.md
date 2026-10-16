# Cloudflare Hosting with GitHub Actions Daily Updates

Cloudflare hosts the static report. GitHub Actions downloads prices, runs the existing Python pipeline and deploys the result directly with Wrangler. Daily updates require no Deploy Hook URL and no Worker runtime credentials.

```text
06:30 Beijing time, Tuesday through Saturday
  → GitHub Actions schedule (UTC Monday-Friday 22:30)
  → Check out main → Download prices → Backtest → Generate dist/
  → Wrangler deploy → Verify the published report matches this build
```

Workflow: [`.github/workflows/update-report.yml`](./.github/workflows/update-report.yml). The strategy, bilingual page, report-data format, temporary-directory build and current price/series checks are unchanged.

## 1. Add two GitHub repository secrets

Create a Cloudflare API token using the **Edit Cloudflare Workers** template, scoped to the account hosting `qqq-strategy-auto-deploy`. Find the Cloudflare account ID in that account’s dashboard. See [Cloudflare’s GitHub Actions authentication guide](https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/#1-authentication).

In the GitHub repository, open **Settings → Secrets and variables → Actions → Repository secrets → New repository secret** and add:

| Secret | Value |
|---|---|
| `CLOUDFLARE_API_TOKEN` | The Cloudflare API token allowed to deploy this Worker |
| `CLOUDFLARE_ACCOUNT_ID` | The account ID hosting this Worker |

Both credentials are stored in GitHub Actions secrets. They are not Worker runtime variables, Cloudflare Builds variables or committed files. The workflow checks for missing credentials before starting production work and exposes them only to the credential-check and production-deployment steps. Pull-request validation does not use them.

A successful Cloudflare Workers Builds deployment does not prove these new GitHub secrets are configured: the two systems authenticate independently.

## 2. Merge the PR, then run once manually

1. Review the feature branch’s checks and Cloudflare preview. The user merges the PR into `main`.
2. Open **GitHub → Actions → Update and deploy report → Run workflow** and choose **main**.
3. Inspect the build, packaging, deployment and published-report verification steps.
4. Open [qqq-strategy.kenzhu.link](https://qqq-strategy.kenzhu.link) and confirm the latest trading date. A successful run’s summary reports the verified date.

The workflow rebuilds the report using `npm run build`, which runs `bash build_cloudflare.sh`. This installs Python dependencies, validates SQLite, downloads prices with up to three attempts, runs the backtest/report pipeline in a temporary directory, and produces four static assets in `dist/`. `npm run check:deploy` validates packaging before `npm run deploy` publishes production.

After deployment, `scripts/verify_deployment.py` fetches `report_data.js` from the production domain using a unique cache-busting query and compares the entire parsed payload against this run’s `dist/report_data.js`. It retries six times for propagation/network delays and fails if the payload still differs, even when the trading date is the same. Verification failure marks the workflow failed; it does not automatically roll back the deployment.

Production runs are restricted to `main`. Choosing a feature branch for a manual run skips the job. Pull requests affecting the pipeline run tests, build the report and check packaging, without deploying production. The workflow does not push generated data, merge PRs or write commits. Concurrent production workflow runs are serialized.

## 3. Retire the old Cloudflare Cron and Hook

After a successful manual GitHub Actions deployment:

- Open **Cloudflare → Workers & Pages → qqq-strategy-auto-deploy → Settings → Triggers / Trigger Events** and remove the old `30 22 * * MON-FRI` Cron.
- Remove unused `DEPLOY_HOOK_URL` entries from runtime variables/secrets and build variables. The old Deploy Hook can also be removed once no other integration uses it.
- Leave the custom domain, Preview URL settings and Workers Builds Git connection in place.

For a safe transition, `cloudflare/worker.mjs` retains a no-op `scheduled()` handler. An old dashboard Cron only logs that updates moved to GitHub Actions; it never calls a Hook, requires credentials or starts another build. A successful legacy Cron event therefore does not mean a daily update ran; use GitHub Actions for daily-update status.

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

Create a missing virtual environment with `python3 -m venv .venv`. `npm run preview` publishes the current feature branch’s preview. Production is published by Cloudflare on merges or by the scheduled/manual GitHub workflow; do not publish an unmerged feature branch to production. `npm run dev` previews locally.

Local regression checks:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/worker.test.mjs
```

Troubleshooting:

- **Missing credentials:** add both repository Actions secrets from Section 1. GitHub names are case-sensitive. Setting variables in Cloudflare Builds or Worker runtime settings does not provide GitHub credentials.
- **No scheduled run:** check that the workflow is on default `main`, Actions is enabled and the workflow is not disabled. Inspect GitHub Actions rather than Cloudflare Cron events.
- **Authentication/deployment failure:** check token scope/account ID and confirm Wrangler `name` matches the existing Worker. Use the Edit Cloudflare Workers template scoped to the correct account.
- **`SQLite driver not installed!`:** Linux x86_64 installs pinned `pysqlite3-binary`; the existing runtime check must succeed before downloads. This compatibility fallback is retained for Cloudflare Builds too.
- **Download/backtest failure:** inspect the corresponding workflow step. Failed build/packaging steps prevent production deployment.
- **Published report mismatch:** inspect deployment output and the production domain’s routing/cache. The verification step checks report values as well as date; rerun on `main` after resolving the cause.
- **Preview 404/1042:** enable Preview URL routing in Cloudflare, then verify the actual page and report data.
