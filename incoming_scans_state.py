#!/usr/bin/env python3
"""
incoming_scans_state.py

Small CLI to update the state file used by incoming_scans_collector.py.
The LLM-driven cron job calls this after it finishes handling (or flagging)
each file in "Incoming Scans", so future runs don't re-process it.

Usage:
    python3 incoming_scans_state.py mark-processed <file_id> --name "..." --result "moved to House/2026"
    python3 incoming_scans_state.py mark-flagged <file_id> --name "..." --reason "no obvious category; need David's input"
    python3 incoming_scans_state.py clear-flag <file_id>          # e.g. once David has answered and it's been filed
    python3 incoming_scans_state.py list                          # dump current state as JSON
"""
import argparse
import json
import os
from datetime import datetime, timezone

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
STATE_DIR = os.path.join(HERMES_HOME, "state")
STATE_FILE = os.path.join(STATE_DIR, "incoming_scans_state.json")


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"processed": {}, "flagged": {}}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"processed": {}, "flagged": {}}


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("mark-processed")
    p1.add_argument("file_id")
    p1.add_argument("--name", default="")
    p1.add_argument("--result", default="")

    p2 = sub.add_parser("mark-flagged")
    p2.add_argument("file_id")
    p2.add_argument("--name", default="")
    p2.add_argument("--reason", default="")

    p3 = sub.add_parser("clear-flag")
    p3.add_argument("file_id")

    sub.add_parser("list")

    args = parser.parse_args()
    state = load_state()
    state.setdefault("processed", {})
    state.setdefault("flagged", {})

    if args.cmd == "mark-processed":
        state["processed"][args.file_id] = {
            "name": args.name,
            "handled_at": now_iso(),
            "result": args.result,
        }
        state["flagged"].pop(args.file_id, None)
        save_state(state)
        print(json.dumps({"status": "ok", "action": "mark-processed", "file_id": args.file_id}))
    elif args.cmd == "mark-flagged":
        state["flagged"][args.file_id] = {
            "name": args.name,
            "flagged_at": now_iso(),
            "reason": args.reason,
        }
        save_state(state)
        print(json.dumps({"status": "ok", "action": "mark-flagged", "file_id": args.file_id}))
    elif args.cmd == "clear-flag":
        state["flagged"].pop(args.file_id, None)
        save_state(state)
        print(json.dumps({"status": "ok", "action": "clear-flag", "file_id": args.file_id}))
    elif args.cmd == "list":
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
