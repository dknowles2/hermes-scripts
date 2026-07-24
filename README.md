# hermes-scripts

Backup copies of cron job collector scripts used by David Knowles' Hermes agent (`elzar`).
These run on a schedule via `hermes cronjob` and feed structured JSON to LLM-driven
sync agents that file/reconcile tasks on a Hermes Kanban board.

Live copies run from `~/.hermes/scripts/` on the agent host. This repo exists purely
as an off-machine backup in case that host is lost — it is not deployed from here.

## Scripts

- **`ha_issue_collector.py`** — Fetches open `home-assistant/core` issues mentioning
  `dknowles2` or labeled `integration: hydrawise` / `integration: schlage`, and files
  kanban tasks per issue. Runs daily via the "HA Core Issue Monitor" cron job.

- **`pr_watcher_collector.py`** — Fetches open PRs across `dknowles2/*` repos via
  `gh api search/issues`, classifies each by author (`dependabot`, `third_party`, or
  `own` — David's own PRs are skipped). Feeds the "PR Watcher" cron job, which:
  - Dependabot PRs → assigns a `watcher` kanban task to diagnose/fix CI failures
    (e.g. new ruff rule violations) or request a rebase on conflicts, escalating to
    David when unsure.
  - Third-party PRs → assigns a `reviewer` kanban task to review the diff and always
    hands final say back to David via PR assignment.

## Updating

When these scripts change on `elzar`, copy the latest version here and push:

```bash
cp ~/.hermes/scripts/*.py /path/to/this/repo/
git add -A && git commit -m "sync: update collector scripts" && git push
```
