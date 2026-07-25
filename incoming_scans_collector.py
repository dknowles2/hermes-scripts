#!/usr/bin/env python3
"""
incoming_scans_collector.py

Collector for the "Incoming Scans" Google Drive automation cron job.

Lists files currently in the "Incoming Scans" Drive folder and diffs them
against a local state file of already-processed (or already-flagged) file
IDs. Prints JSON describing only the files that still need attention, so
the LLM-driven cron job doesn't have to re-reason about files it already
filed (or already flagged for David).

State file: ~/.hermes/state/incoming_scans_state.json
  {
    "processed": {"<file_id>": {"name": "...", "handled_at": "...", "result": "moved"}},
    "flagged":   {"<file_id>": {"name": "...", "flagged_at": "...", "reason": "..."}}
  }

Usage:
    python3 incoming_scans_collector.py

Output (stdout): JSON
  {
    "incoming_scans_folder_id": "...",
    "new_files": [{"id", "name", "createdTime", "modifiedTime", "size"}, ...],
    "flagged_files": [{"id", "name", "reason", "flagged_at"}, ...],
    "counts": {"new": N, "flagged": N, "processed_total": N}
  }

flagged_files are files David still needs to weigh in on (ambiguous
categorization from a prior run). They are re-surfaced every run until
resolved, so the cron prompt can gently remind David rather than silently
dropping them.
"""
import json
import os
import sys

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
GOOGLE_API_SCRIPT = os.path.join(
    HERMES_HOME, "skills", "productivity", "google-workspace", "scripts", "google_api.py"
)
STATE_DIR = os.path.join(HERMES_HOME, "state")
STATE_FILE = os.path.join(STATE_DIR, "incoming_scans_state.json")
INCOMING_SCANS_FOLDER_ID = "0B3j_PjDTxot7ZDl4ZVNNcENXUzQ"  # "Incoming Scans" folder


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"processed": {}, "flagged": {}}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"processed": {}, "flagged": {}}


def main():
    sys.path.insert(
        0, os.path.join(HERMES_HOME, "skills", "productivity", "google-workspace", "scripts")
    )
    from google_api import build_service  # noqa: E402

    state = load_state()
    processed_ids = set(state.get("processed", {}).keys())
    flagged = state.get("flagged", {})

    service = build_service("drive", "v3")
    res = (
        service.files()
        .list(
            q=f"'{INCOMING_SCANS_FOLDER_ID}' in parents and trashed=false",
            pageSize=200,
            fields="files(id, name, mimeType, createdTime, modifiedTime, size)",
        )
        .execute()
    )
    files = res.get("files", [])

    new_files = []
    for f in files:
        if f["id"] in processed_ids:
            continue
        if f["id"] in flagged:
            continue  # surfaced separately below
        if f.get("mimeType") != "application/pdf":
            continue  # this automation only handles scanned PDFs
        new_files.append(
            {
                "id": f["id"],
                "name": f["name"],
                "createdTime": f.get("createdTime"),
                "modifiedTime": f.get("modifiedTime"),
                "size": f.get("size"),
            }
        )

    flagged_files = [
        {"id": fid, "name": info.get("name"), "reason": info.get("reason"), "flagged_at": info.get("flagged_at")}
        for fid, info in flagged.items()
    ]

    output = {
        "incoming_scans_folder_id": INCOMING_SCANS_FOLDER_ID,
        "new_files": new_files,
        "flagged_files": flagged_files,
        "counts": {
            "new": len(new_files),
            "flagged": len(flagged_files),
            "processed_total": len(processed_ids),
        },
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
