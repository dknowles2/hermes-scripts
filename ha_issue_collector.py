import subprocess
import json
import sys

WORKSPACE = "worktree:/home/dknowles/workspace/core"
ASSIGNEE = "watcher"


def run_gh(command):
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return res.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running: {command}\n{e.stderr}", file=sys.stderr)
        return ""


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
        print(f"[{board}] #{issue_number}: {res.stdout.strip()}")
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

    # 4. Create kanban tasks
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

        for board in boards:
            create_task(board, num, title or f"Issue #{num}", url, body_excerpt)


if __name__ == "__main__":
    main()
