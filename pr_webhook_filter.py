import sys
import json


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

    title = pr.get("title", "")
    url = pr.get("html_url", "")
    number = pr.get("number")

    print(f"""An event occurred on GitHub PR: {url}
Action: {action} (author: {author}, repo: {repo_full_name})
Title: {title}

Please inspect and review this PR immediately using your PR Watcher instructions:
1. Check if an automated review has already been submitted for the current HEAD commit (`already_reviewed`).
2. If this is a Dependabot PR: fix trivial lint/CI issues and push, or comment @dependabot rebase on conflicts, or escalate to dknowles2 on GitHub.
3. If this is a third-party PR: review the diff (`gh pr diff {number} --repo {repo_full_name}`).
   - Include "LGTM" if good to merge.
   - Tag *(Automated review via Hermes Reviewer Agent)*.
   - If changes are requested, DO NOT assign dknowles2.
   - If LGTM or manual intervention needed, assign dknowles2 on GitHub with a clear Recommendation.
4. Update/reconcile the default kanban task.""")


if __name__ == "__main__":
    main()
