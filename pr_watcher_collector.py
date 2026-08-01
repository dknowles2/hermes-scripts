import subprocess
import json
import sys

OWNER = "dknowles2"

# Repos to skip entirely (no kanban tasks filed, no gh calls made).
IGNORED_REPOS = {"dknowles2/ha-shady"}


def run_gh(command):
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return res.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running: {command}\n{e.stderr}", file=sys.stderr)
        return ""


def classify(author):
    if author == "dependabot[bot]":
        return "dependabot"
    if author == OWNER:
        return "own"
    return "third_party"


def main():
    raw = run_gh(f'gh api "search/issues?q=is:pr+is:open+-is:draft+user:{OWNER}&per_page=100"')
    prs = []
    if raw:
        try:
            data = json.loads(raw)
            for item in data.get("items", []):
                if item.get("draft"):
                    continue  # Ignore draft PRs
                author = item.get("user", {}).get("login", "")
                category = classify(author)
                if category == "own":
                    continue  # David's own PRs are ignored entirely

                repo_url = item.get("repository_url", "")
                repo = repo_url.split("/repos/")[-1] if "/repos/" in repo_url else ""
                if repo in IGNORED_REPOS:
                    continue
                number = item.get("number")
                title = item.get("title", "")
                url = item.get("html_url", "")
                body = item.get("body", "") or ""
                if len(body) > 1500:
                    body = body[:1500] + "... [trimmed]"
                labels = [l.get("name") for l in item.get("labels", [])]

                # Fetch mergeable/CI status for extra context
                detail_raw = run_gh(
                    f'gh pr view {number} --repo {repo} --json mergeable,statusCheckRollup,mergeStateStatus,isDraft'
                )
                mergeable = ""
                checks_summary = ""
                if detail_raw:
                    try:
                        detail = json.loads(detail_raw)
                        if detail.get("isDraft"):
                            continue  # Double-check draft status
                        mergeable = detail.get("mergeStateStatus", "") or detail.get("mergeable", "")
                        rollup = detail.get("statusCheckRollup", []) or []
                        failing = [c.get("name", c.get("context", "?")) for c in rollup
                                   if c.get("conclusion") not in (None, "SUCCESS", "NEUTRAL", "SKIPPED")]
                        checks_summary = f"failing: {', '.join(failing)}" if failing else "all checks passing (or none reported)"
                    except Exception as e:
                        print(f"Error parsing pr view for {repo}#{number}: {e}", file=sys.stderr)

                prs.append({
                    "repo": repo,
                    "number": number,
                    "title": title,
                    "url": url,
                    "author": author,
                    "category": category,
                    "labels": labels,
                    "body": body,
                    "merge_state": mergeable,
                    "checks": checks_summary,
                })
        except Exception as e:
            print(f"Error parsing search results: {e}", file=sys.stderr)

    print(json.dumps({"prs": prs}, indent=2))


if __name__ == "__main__":
    main()
