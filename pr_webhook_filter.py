import sys
import json
import subprocess


def main():
    try:
        raw = sys.stdin.read()
        if not raw:
            return
        payload = json.loads(raw)
    except Exception:
        return

    pr = payload.get("pull_request")
    if not pr:
        return

    action = payload.get("action", "")
    if action not in ("opened", "synchronize", "reopened"):
        return

    if pr.get("draft"):
        return  # Skip draft PRs

    author = pr.get("user", {}).get("login", "")
    if author == "dknowles2":
        return  # Skip David's own PRs

    repo_full_name = payload.get("repository", {}).get("full_name", "")
    if repo_full_name == "dknowles2/ha-shady":
        return  # Ignored repo

    # Instantly trigger the PR Watcher cron job (ff1ac1d8dfe9) in the background.
    # The cron job runs with full terminal, gh CLI, web, and kanban toolsets.
    try:
        subprocess.Popen(
            ["hermes", "cron", "run", "ff1ac1d8dfe9"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        sys.stderr.write(f"Error triggering PR Watcher cron job: {e}\n")

    # Return [SILENT] so the webhook route returns 200 OK without spawning a toolless agent turn
    print("[SILENT]")


if __name__ == "__main__":
    main()
