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
  Also auto-applies the appropriate `integration: <name>` label to an issue if it's
  missing one — **except** it never applies labels to `home-assistant/core`
  (guarded via `NEVER_LABEL_REPOS`, since David doesn't maintain that repo). This
  is currently a no-op in practice since that's the only repo this script touches;
  the guard exists so it's safe if the script's scope ever expands.

- **`pr_watcher_collector.py`** — Fetches open PRs across `dknowles2/*` repos via
  `gh api search/issues`, classifies each by author (`dependabot`, `third_party`, or
  `own` — David's own PRs are skipped). Also skips repos in `IGNORED_REPOS`
  entirely (currently `dknowles2/ha-shady`). Feeds the "PR Watcher" cron job, which:
  - Dependabot PRs → assigns a `watcher` kanban task to diagnose/fix CI failures
    (e.g. new ruff rule violations) or request a rebase on conflicts, escalating to
    David when unsure.
  - Third-party PRs → assigns a `reviewer` kanban task to review the diff and always
    hands final say back to David via PR assignment.

- **`incoming_scans_collector.py`** — Lists PDFs currently sitting in David's
  "Incoming Scans" Google Drive folder (fed by his `gdrive_sync` scanner
  pipeline: Samba share → OCR → Drive upload) that haven't yet been filed,
  diffed against local state at `~/.hermes/state/incoming_scans_state.json`.
  Also re-surfaces previously flagged files David hasn't answered yet.
  Feeds the "Incoming Scans Sorter" cron job (LLM-driven — the agent reads
  each scan's OCR'd text, determines a description/date, renames it, and
  files it into the matching folder in David's real Drive taxonomy
  (Car/House/Medical/Jacob/Legal/etc.), creating a new dated subfolder if a
  clear year/person pattern exists but the specific one is missing. If no
  category fits and "Misc" doesn't feel right, the agent flags the file and
  asks David instead of guessing.

- **`incoming_scans_state.py`** — Companion CLI the sorter agent uses to
  record outcomes (`mark-processed`, `mark-flagged`, `clear-flag`) against
  the state file so already-handled files aren't reprocessed.

## Cron job definitions

`cron-jobs/` holds restorable specs (schedule, toolsets, model, and the full
prompt text) for each cron job that drives these scripts, since the jobs
themselves live only in Hermes's internal cron store (`~/.hermes/cron/`) on
`elzar` and aren't otherwise version-controlled:

- **`cron-jobs/ha_issue_monitor.md`** — HA Core Issue Monitor (daily 9am)
- **`cron-jobs/pr_watcher.md`** — PR Watcher (daily 10am)
- **`cron-jobs/incoming_scans_sorter.md`** — Incoming Scans Sorter (daily 8am)

These are not auto-synced — if a job's prompt/schedule/config changes on
`elzar`, update the corresponding file here manually.

## Updating

When these scripts or cron job configs change on `elzar`, copy the latest
version here and push:

```bash
cp ~/.hermes/scripts/*.py /path/to/this/repo/
# manually update cron-jobs/*.md to match any prompt/schedule changes
git add -A && git commit -m "sync: update collector scripts and cron job specs" && git push
```
