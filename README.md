# NewsPulse

A self-updating news & entertainment magazine that runs forever on $0 of infrastructure.

NewsPulse pulls the latest headlines and stories from 37 public RSS/Atom feeds across 10 categories (World, India, Tech, Business, Sports, Gaming, Music, Movies, Science, Entertainment), builds a fast static site, notifies search engines, commits the fresh data, and deploys to GitHub Pages — automatically, every two hours, with no servers, no paid services, and no secrets to manage.

**Live site:** https://abhishekanandsupreme-rgb.github.io/news-pulse/

---

## How it updates itself

[`.github/workflows/update.yml`](.github/workflows/update.yml) is the heartbeat. Every 2 hours (and on every code push) GitHub Actions runs the full pipeline:

| # | Stage | What happens |
|---|-------|--------------|
| 1 | Fetch | `scripts/fetch_feeds.py` pulls the latest stories into `data/` |
| 2 | Build | `scripts/build_site.py` regenerates the static site into `docs/` |
| 3 | Verify | `scripts/docs-check.py` fails the run if the build is empty or broken |
| 4 | SEO | `scripts/submit_seo.py submit …` pings IndexNow/Bing — **never blocks the deploy** (`continue-on-error`) |
| 5 | Commit | fresh `data/` is pushed to `master` with the built-in `GITHUB_TOKEN` |
| 6 | Deploy | `docs/` ships to GitHub Pages via the official Pages actions |

The cadence is one line in the workflow — change `7 */2 * * *` to run more or less often. (Minute 7 keeps the run out of GitHub's busiest top-of-hour cron window, so the schedule fires closer to on time.)

## Why it's free

- Public repository → GitHub Actions minutes are free
- GitHub Pages hosting for public repos is free
- The pipeline authenticates with the built-in `GITHUB_TOKEN` — nothing to create, store, or rotate
- Everything is Python 3.11 **stdlib only** — there is no `pip install` step to break

## The 60-day keepalive

GitHub automatically disables scheduled workflows in public repositories after **60 days with no repository activity**. NewsPulse is immune by design:

- Every run that finds new stories commits `data/` → activity.
- If the feeds go quiet, a `data/.heartbeat` timestamp refreshes itself after 30 idle days, guaranteeing a commit well inside the 60-day window.

A monthly Dependabot PR (`.github/dependabot.yml`) keeps the pinned GitHub Actions versions current, so the pipeline keeps working as GitHub evolves.

## Repository layout

```
.github/workflows/update.yml    the automation: cron -> build -> deploy
.github/dependabot.yml          monthly PRs to keep the actions current
scripts/fetch_feeds.py          pull stories from feeds into data/
scripts/build_site.py           generate the static site into docs/
scripts/submit_seo.py           ping search engines with the sitemap
scripts/docs-check.py           sanity-check the build before it ships
data/                           committed snapshots of the fetched stories
docs/                           generated site — deployed from the workflow
                                artifact, so it is never auto-committed
```

## Running locally

Python 3.11 stdlib only — no virtualenv, no pip.

```
python scripts/fetch_feeds.py     # refresh data/
python scripts/build_site.py     # rebuild docs/
python scripts/docs-check.py      # verify the build (add --strict to require sitemap.xml)
python scripts/submit_seo.py      # dry-run; add --submit to actually ping
```

## Manual run

Actions tab → **Update NewsPulse** → Run workflow. Tick **Skip the search-engine submission step** to test the pipeline without pinging search engines.

## One-time setup (already configured)

- Settings → Pages → Build and deployment → Source: **GitHub Actions**
- The workflow's own `permissions:` block grants `contents: write`, `pages: write` and `id-token: write`, so no repository-wide permission changes are needed.

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| Site not updating | Check the Actions tab for failed runs; each stage's log names the exact script that failed |
| "Push rejected" in the commit step | The workflow auto-rebases once and retries; if that also fails, the next scheduled run recovers |
| SEO step failed but site deployed | By design — SEO never blocks deploy. Check its log if it persists |
| "Scheduled workflow disabled" email | Only possible if the repo is untouched for 60 days; any push re-enables it (see the keepalive above) |

## License

MIT — see [LICENSE](LICENSE).
