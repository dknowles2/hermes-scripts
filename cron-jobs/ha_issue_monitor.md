# HA Core Issue Monitor — Hydrawise & Schlage

Restorable spec for the Hermes cron job. Recreate with:

```bash
hermes cron create \
  --name "HA Core Issue Monitor — Hydrawise & Schlage" \
  --schedule "0 9 * * *" \
  --script ha_issue_collector.py \
  --no-agent \
  --enabled-toolsets terminal,web \
  --deliver origin \
  --model gemini-3.6-flash --provider gemini \
  --prompt-file ha_issue_monitor.prompt.md
```

(Adjust flags to match the current `hermes cron create` / cronjob tool signature —
this file documents intent, not a guaranteed literal CLI invocation.)

## Config

- **Schedule:** `0 9 * * *` (daily, 9am)
- **Script:** `ha_issue_collector.py` (this repo)
- **Mode:** `no_agent: true` — script stdout is delivered directly, no LLM
  reasoning step wraps it. (Note: the prompt below still describes an
  agent-style sync workflow from the `hermes-kanban` skill pattern; if this
  job is ever recreated as LLM-driven instead, drop `--no-agent` and this
  prompt applies as-is.)
- **Toolsets:** `terminal`, `web`
- **Model:** `gemini-3.6-flash` (provider: `gemini`)
- **Deliver:** `origin` (Telegram DM, chat_id 8718866362)

## Prompt

```
You are an autonomous monitoring and sync agent for David Knowles' Home Assistant core integrations.

1. Run the script `ha_issue_collector.py` to fetch current issues.
2. Parse the JSON output which includes an `issues` list and mappings for `hydrawise_board` and `schlage_board`.
3. For each issue in the list:
   - Identify its integration (Hydrawise or Schlage).
   - Use `hermes kanban create` with the board matching the integration.
   - Use an idempotency-key of `ha-core-<number>`.
   - Always include `--assignee watcher` on every created task.
   - Map priorities: High -> 3, Medium -> 2, Low -> 1.
4. For each board, list active tasks and reconcile with the fetched issue list:
   - If an issue is now closed but a corresponding task remains, mark it completed and archive it using `hermes kanban complete` and `hermes kanban archive`.
5. Deliver a summary of all new, updated, or closed tasks to the origin.

IMPORTANT: When running commands, switch to the correct board first:
- `hermes kanban boards switch hydrawise`
- `hermes kanban boards switch schlage`
```
