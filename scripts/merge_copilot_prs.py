#!/usr/bin/env python3
"""
Merge Copilot-created PRs on kwalus/Canopy and delete their branches.

Prerequisites:
- PRs must be marked "Ready for review" (not draft) on GitHub.
  Draft PRs return 405; use the GitHub UI to click "Ready for review" on each PR.
- If a PR has failing CI checks, either fix the branch or temporarily allow
  merging with failing checks in repo Settings → Branches → main.

Usage:
  python scripts/merge_copilot_prs.py           # merge PRs 1 and 2, delete branches
  python scripts/merge_copilot_prs.py --dry-run # only list and report mergeable state
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

MANAGER = "http://localhost:8000"
OWNER = "kwalus"
REPO = "Canopy"
# PR numbers from list_pull_requests (Copilot agentic)
PR_NUMBERS = [1, 2]


def mgr_call(tool, args, timeout=45):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "call_tool", "arguments": {"server": "github", "tool": tool, "arguments": args}},
    }
    req = urllib.request.Request(
        MANAGER,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get_inner(r):
    text = r.get("result", {}).get("content", [{}])[0].get("text", "{}")
    data = json.loads(text) if isinstance(text, str) and text.strip().startswith("{") else {}
    return data.get("result", data)


def main():
    parser = argparse.ArgumentParser(description="Merge Copilot PRs and delete branches")
    parser.add_argument("--dry-run", action="store_true", help="Only report state, do not merge")
    args = parser.parse_args()
    dry = args.dry_run

    for pr_num in PR_NUMBERS:
        r = mgr_call("get_pull_request", {"owner": OWNER, "repo": REPO, "pr_number": pr_num})
        inner = get_inner(r)
        pr = inner.get("pull_request", {})
        title = (pr.get("title") or "")[:60]
        draft = pr.get("draft", True)
        mergeable = pr.get("mergeable")
        head_ref = (pr.get("head") or {}).get("ref", "") if isinstance(pr.get("head"), dict) else ""

        print(f"PR #{pr_num}: {title}")
        print(f"  draft={draft}, mergeable={mergeable}, head={head_ref}")

        if dry:
            if draft:
                print("  → Mark as Ready for review on GitHub to allow merge.")
            continue

        if draft:
            print("  Skipped (still draft). Mark Ready for review on GitHub, then re-run.")
            continue

        print(f"  Merging PR #{pr_num}...")
        r = mgr_call("merge_pull_request", {
            "owner": OWNER,
            "repo": REPO,
            "pr_number": pr_num,
            "merge_method": "squash",
        })
        inner = get_inner(r)
        if inner.get("merged", inner.get("success", False)):
            print("  Merged.")
            if head_ref:
                r2 = mgr_call("delete_branch", {"owner": OWNER, "repo": REPO, "branch_name": head_ref})
                inner2 = get_inner(r2)
                if inner2.get("success", True):
                    print(f"  Branch {head_ref} deleted.")
                else:
                    print(f"  Delete branch failed: {inner2}")
        else:
            err = inner.get("error", str(inner)[:200])
            print(f"  Merge failed: {err}")
            if "draft" in str(err).lower():
                print("  → Mark PR as Ready for review on GitHub, then re-run.")
            elif "required status" in str(err).lower() or "checks" in str(err).lower():
                print("  → Fix failing checks on the branch or allow merge with failing checks in repo Settings.")

    if dry:
        print("\nRun without --dry-run to merge and delete branches.")


if __name__ == "__main__":
    main()
