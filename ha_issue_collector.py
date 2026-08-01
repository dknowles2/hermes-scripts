import subprocess
import json
import sys

WORKSPACE = "worktree:/home/dknowles/workspace/core"
ASSIGNEE = "watcher"
REPO = "home-assistant/core"

NEVER_LABEL_REPOS = {"home-assistant/core"}

INTEGRATION_LABELS = {
    "hydrawise": "integration: hydrawise",
    "schlage": "integration: schlage",
}


def run_gh(command):
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return res.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running: {command}\n{e.stderr}", file=sys.stderr)
        return ""


def ensure_label(repo, issue_number, integration, current_labels):
    """Apply the appropriate integration label if the issue doesn't already
    have one. Never touches repos in NEVER_LABEL_REPOS."""
    if repo in NEVER_LABEL_REPOS:
        return

    label = INTEGRATION_LABELS.get(integration)
    if not label:
        return

    has_integration_label = any(
        l.lower().startswith("integration:") for l in current_labels
    )
    if has_integration_label:
        return

    cmd = f'gh issue edit {issue_number} --repo {repo} --add-label "{label}"'
    try:
        subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        print(f"Applied label {label!r} to {repo}#{issue_number}")
    except subprocess.CalledProcessError as e:
        print(f"Error applying label to {repo}#{issue_number}: {e.stderr}", file=sys.stderr)


def create_task(board, issue_number, title, url, body_excerpt=""):
    body = f"GitHub: {url}"
    if body_excerpt:
        body += f"\n\n{body_excerpt}"

    cmd = [
        "hermes", "kanban", "--board", board,
        "create",
        "--workspace", WORKSPACE,
        "--idempotency-key", f"ha-core-{issue_number}",
        "--assignee", ASSIGNEE,
        "--body", body,
        title,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[{board}] New issue #{issue_number}: {title} ({url})")
    except subprocess.CalledProcessError as e:
        print(f"Error creating task for #{issue_number} on {board}: {e.stderr}", file=sys.stderr)


def detect_boards(source, title, body=""):
    boards = set()
    combined = f"{source} {title} {body}".lower()
    if "hydrawise" in combined:
        boards.add("hydrawise")
    if "schlage" in combined:
        boards.add("schlage")
    return boards


def get_existing_board_tasks(board):
    cmd = ["hermes", "kanban", "--board", board, "list", "--json", "--archived"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        tasks = json.loads(res.stdout)
        issue_nums = {}
        for t in tasks:
            title = t.get("title", "")
            if "#" in title:
                try:
                    num_str = title.split("#", 1)[1].split(":", 1)[0].strip()
                    if num_str.isdigit():
                        issue_nums[int(num_str)] = t
                except Exception:
                    pass
        return issue_nums
    except Exception as e:
        print(f"Error fetching existing tasks for {board}: {e}", file=sys.stderr)
        return {}


def main():
    issues_by_num = {}

    # 1. Fetch issues mentioning dknowles2
    raw = run_gh('gh api "repos/home-assistant/core/issues?state=open&mentioned=dknowles2&per_page=50"')
    if raw:
        try:
            for item in json.loads(raw):
                num = item.get("number")
                if num:
                    issues_by_num[num] = {
                        "title": item.get("title", ""),
                        "url": item.get("html_url", ""),
                        "source": "mention",
                    }
        except Exception as e:
            print(f"Error parsing mentioned issues: {e}", file=sys.stderr)

    # 2. Fetch Hydrawise-labeled issues
    raw = run_gh('gh search issues --repo home-assistant/core --state open --label "integration: hydrawise" --json number,title,url')
    if raw:
        try:
            for item in json.loads(raw):
                num = item.get("number")
                if num:
                    if num not in issues_by_num:
                        issues_by_num[num] = {"title": item.get("title", ""), "url": item.get("url", ""), "source": "label:hydrawise"}
                    else:
                        issues_by_num[num]["source"] += ", label:hydrawise"
        except Exception as e:
            print(f"Error parsing hydrawise search: {e}", file=sys.stderr)

    # 3. Fetch Schlage-labeled issues
    raw = run_gh('gh search issues --repo home-assistant/core --state open --label "integration: schlage" --json number,title,url')
    if raw:
        try:
            for item in json.loads(raw):
                num = item.get("number")
                if num:
                    if num not in issues_by_num:
                        issues_by_num[num] = {"title": item.get("title", ""), "url": item.get("url", ""), "source": "label:schlage"}
                    else:
                        issues_by_num[num]["source"] += ", label:schlage"
        except Exception as e:
            print(f"Error parsing schlage search: {e}", file=sys.stderr)

    # Fetch existing board tasks to avoid re-announcing known issues
    existing_by_board = {
        "hydrawise": get_existing_board_tasks("hydrawise"),
        "schlage": get_existing_board_tasks("schlage"),
    }

    # 4. Create kanban tasks for new issues
    for num, info in issues_by_num.items():
        source = info["source"]
        title = info["title"]
        url = info["url"]
        body_excerpt = ""

        boards = detect_boards(source, title)

        # For mentions without a clear integration, fetch issue body to check
        if not boards and "mention" in source:
            detail_raw = run_gh(f"gh issue view {num} --repo home-assistant/core --json title,body,url")
            if detail_raw:
                try:
                    detail = json.loads(detail_raw)
                    body_text = detail.get("body", "")
                    url = detail.get("url") or url
                    boards = detect_boards(source, title, body_text)
                    if body_text:
                        body_excerpt = body_text[:500] + ("..." if len(body_text) > 500 else "")
                except Exception as e:
                    print(f"Error parsing details for #{num}: {e}", file=sys.stderr)

        if not boards:
            print(f"Skipping #{num} ({title!r}) — integration unknown", file=sys.stderr)
            continue

        label_raw = run_gh(f"gh issue view {num} --repo {REPO} --json labels")
        current_labels = []
        if label_raw:
            try:
                current_labels = [l.get("name", "") for l in json.loads(label_raw).get("labels", [])]
            except Exception as e:
                print(f"Error parsing labels for #{num}: {e}", file=sys.stderr)

        for board in boards:
            ensure_label(REPO, num, board, current_labels)
            # Only create task and announce if it doesn't already exist on the board
            if num not in existing_by_board.get(board, {}):
                create_task(board, num, title or f"Issue #{num}", url, body_excerpt)

    # 5. Reconcile closed issues
    for board, existing_tasks in existing_by_board.items():
        for num, task in existing_tasks.items():
            task_id = task.get("id")
            status = task.get("status")
            if status != "archived" and num not in issues_by_num:
                try:
                    subprocess.run(["hermes", "kanban", "--board", board, "complete", task_id], capture_output=True, check=True)
                    subprocess.run(["hermes", "kanban", "--board", board, "archive", task_id], capture_output=True, check=True)
                    print(f"[{board}] Closed issue #{num}: archived task {task_id}")
                except Exception as e:
                    print(f"Error archiving task {task_id} for #{num} on {board}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
