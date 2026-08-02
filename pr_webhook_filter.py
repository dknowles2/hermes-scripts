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

    print(f"""New real-time GitHub PR event received for {repo_full_name}#{number}: {url}
Action: {action} (author: {author})
Title: {title}

Please process this PR immediately:
1. Check if an automated review has already been submitted for the current HEAD commit (`already_reviewed`).
2. If this is a Dependabot PR: fix trivial lint/CI issues and push, or comment @dependabot rebase on conflicts, or escalate to dknowles2 on GitHub.
3. If this is a third-party PR: review the diff (`gh pr diff {number} --repo {repo_full_name}`).
   - Include "LGTM" if good to merge.
   - Tag *(Automated review via Hermes Reviewer Agent)*.
   - If changes are requested: DO NOT assign dknowles2 on GitHub; wait for author commits.
   - If LGTM or manual intervention needed: assign dknowles2 on GitHub with a clear Recommendation.
4. Update/reconcile the default kanban task.
5. TELEGRAM THREAD DIRECTIVE: When notifying David about this PR or asking a question, ALWAYS start a NEW Telegram thread using:
   `hermes send --to telegram:8718866362:new --subject "[PR Review] {repo_full_name}#{number}: {title}" "<message>"`
   so each new PR gets its own dedicated Telegram chat thread.""")


if __name__ == "__main__":
    main()
