#!/usr/bin/env python3
"""
Create GitHub issues for Copilot agentic review tasks via MCP Manager.

Run after pushing production-readiness (and Codex amendment) changes to GitHub.
Creates one issue per review focus so Copilot can run targeted reviews; you can
cherry-pick from resulting PRs.

**Agent note (see .cursorrules):** On this machine the MCP Manager is at
http://localhost:8000 and is already running. Use that URL; no need to start
or discover the manager.

Prerequisites:
  - MCP Manager at http://localhost:8000 (default; already running on this machine)
  - GitHub authenticated in MCP Manager

Usage:
  python scripts/create_copilot_review_issues_mcp.py [--owner OWNER] [--repo REPO] [--mcp-url URL]
  python scripts/create_copilot_review_issues_mcp.py --dry-run   # print issue titles/bodies only
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    Request, urlopen, HTTPError, URLError = None, None, None, None

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Label for all Copilot review issues (optional; create in repo or use --no-labels)
REVIEW_LABEL = "copilot-review"

# One issue per focus area. Title and body are used for create_issue(owner, repo, title, body=..., labels=...).
COPILOT_REVIEW_TASKS = [
    {
        "title": "[Copilot Review] Usability — flows, clarity, and ease of use",
        "body": """**Context:** Post production-readiness and Codex amendments. This issue is for a Copilot agentic review pass.

**Focus: Usability**
- Identify any flows that are confusing, multi-step when they could be simpler, or missing feedback.
- Check first-run setup, login, registration, and Connect (invite/peer) flows for clarity.
- Note any copy, tooltips, or error messages that could be clearer.
- Suggest improvements only; do not change behavior without follow-up alignment.

**Deliverable:** Open a PR with a short usability report (markdown) and optional small, non-breaking UX tweaks. If you only report findings, that’s fine too.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot Review] Mesh stability — P2P reconnect, routing, and reliability",
        "body": """**Context:** Post production-readiness and Codex amendments. This issue is for a Copilot agentic review pass.

**Focus: Mesh stability**
- Review reconnect logic, backoff, and cold-peer behavior in `canopy/network/manager.py` and related code.
- Check rate limiting and pruning in `canopy/network/routing.py` for correctness and edge cases.
- Look for races, unbounded growth, or resource leaks in connection/message handling.
- Consider Windows vs macOS/Linux behavior if documented or obvious from code.

**Deliverable:** Open a PR with a short stability report and any low-risk fixes (with clear comments). Prefer reporting over invasive changes.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot Review] User friendliness and cross compatibility",
        "body": """**Context:** Post production-readiness and Codex amendments. This issue is for a Copilot agentic review pass.

**Focus: User friendliness and cross compatibility**
- Assess install/setup experience (install.sh, start script, docs) on different environments (Linux, macOS, Windows).
- Check Python version and dependency assumptions (e.g. 3.10+).
- Identify any platform-specific bugs or docs gaps (paths, shells, permissions).
- Suggest small improvements to docs or scripts for clarity and portability.

**Deliverable:** Open a PR with a short compatibility report and optional doc/script tweaks. No core logic changes unless critical.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot Review] Login, auth, and session issues",
        "body": """**Context:** Post production-readiness and Codex amendments. This issue is for a Copilot agentic review pass.

**Focus: Login and auth**
- Review login, logout, registration, and /setup flows for edge cases (expired session, concurrent tabs, back button).
- Check rate limiting on login/register and CSRF handling; ensure no legitimate flows are blocked.
- Look for any session or cookie handling that could be improved for security or UX.
- Verify password rules and change-password flow are consistent and clear.

**Deliverable:** Open a PR with a short auth/session report and optional small fixes. Prefer reporting security concerns clearly.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot Review] Profiles and post propagation",
        "body": """**Context:** Post production-readiness and Codex amendments. This issue is for a Copilot agentic review pass.

**Focus: Profiles and post propagation**
- Review how profiles (display name, avatar, theme) propagate across the mesh and to the UI.
- Check feed post creation, visibility, and propagation; ensure edits/expiry/deletes propagate correctly.
- Look for inconsistencies between local view and what remote peers see (e.g. ordering, missing updates).
- Note any scaling or ordering concerns with large feeds or many peers.

**Deliverable:** Open a PR with a short propagation report and optional targeted fixes. Avoid broad refactors.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot Review] Scaling and performance",
        "body": """**Context:** Post production-readiness and Codex amendments. This issue is for a Copilot agentic review pass.

**Focus: Scaling**
- Identify bottlenecks or unbounded structures (DB, in-memory caches, message queues).
- Check indexes and queries in hot paths (feed, channels, messages).
- Consider behavior with many peers, many channels, or large message history.
- Suggest conservative improvements (e.g. limits, indexes, batching) without redesign.

**Deliverable:** Open a PR with a short scaling/performance report and optional low-risk optimizations.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot Review] UI behavior and layout",
        "body": """**Context:** Post production-readiness and Codex amendments. This issue is for a Copilot agentic review pass.

**Focus: UI behavior and layout**
- Review key pages (dashboard, feed, channels, messages, Connect, settings) for layout issues, overflow, or broken responsive behavior.
- Check modals, dropdowns, and sidebar on different viewport sizes.
- Look for focus management, keyboard use, and accessibility where obvious.
- Note any JS errors or missing null checks that could break the UI.

**Deliverable:** Open a PR with a short UI report and optional small CSS/HTML/JS fixes. No large redesigns.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot Review] Aesthetics and theme consistency",
        "body": """**Context:** Post production-readiness and Codex amendments. This issue is for a Copilot agentic review pass.

**Focus: Aesthetics**
- Review theme consistency (dark, liquid-glass, eco, etc.) across pages and components.
- Check contrast, typography, and spacing for readability and consistency.
- Note any components that don’t respect theme variables or look out of place.
- Suggest small, consistent tweaks; avoid subjective style wars.

**Deliverable:** Open a PR with a short aesthetics report and optional small theme/CSS tweaks.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot Review] Review existing collaborator PR(s)",
        "body": """**Context:** There is at least one open PR from a Canopy collaborator. This issue is for a Copilot agentic review of that PR (or those PRs).

**Focus: Collaborator PR review**
- List open PRs in this repo from collaborators (e.g. filter by author or label if applicable).
- Review the diff for: correctness, consistency with codebase style, security, and backward compatibility.
- Check that tests/docs are updated if behavior changes.
- Post a short review summary as a comment on the PR (or in this issue) and suggest any changes.

**Deliverable:** A review comment on the collaborator PR and optionally a short summary in this issue. No new PR required unless you propose follow-up issues.""",
        "labels": [REVIEW_LABEL],
    },
]


def rpc_call(url: str, method: str, params: dict) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tool_call(url: str, server: str, tool: str, arguments: dict) -> dict:
    res = rpc_call(
        url,
        "tools/call",
        {"name": "call_tool", "arguments": {"server": server, "tool": tool, "arguments": arguments}},
    )
    text = (res.get("result") or {}).get("content") or []
    if not text or not isinstance(text[0].get("text"), str):
        return {"success": False, "error": res.get("error") or "No result content"}
    return json.loads(text[0]["text"])


def main():
    ap = argparse.ArgumentParser(description="Create Copilot review issues via MCP Manager")
    ap.add_argument("--owner", default="kwalus", help="GitHub repo owner")
    ap.add_argument("--repo", default="Canopy", help="GitHub repo name")
    ap.add_argument("--mcp-url", default="http://localhost:8000", help="MCP Manager URL (on this machine: localhost:8000, already running)")
    ap.add_argument("--dry-run", action="store_true", help="Print issue titles/bodies only; do not create")
    ap.add_argument("--no-labels", action="store_true", help="Do not add labels (use if copilot-review label does not exist)")
    ap.add_argument("--assign-copilot", action="store_true", help="After creating issues, assign Copilot to each via assign_copilot_to_issue (MCP GitHub server)")
    args = ap.parse_args()
    url = args.mcp_url.rstrip("/")

    if args.no_labels:
        for t in COPILOT_REVIEW_TASKS:
            t["labels"] = []

    if args.dry_run:
        for i, task in enumerate(COPILOT_REVIEW_TASKS, 1):
            print(f"--- Issue {i}: {task['title']} ---")
            print(task["body"][:400] + "..." if len(task["body"]) > 400 else task["body"])
            print()
        print(f"Total: {len(COPILOT_REVIEW_TASKS)} issues. Run without --dry-run to create via MCP.")
        return 0

    created_numbers = []
    for i, task in enumerate(COPILOT_REVIEW_TASKS, 1):
        title = task["title"]
        body = task["body"]
        labels = task.get("labels") or []
        print(f"[{i}/{len(COPILOT_REVIEW_TASKS)}] Creating: {title[:60]}...", file=sys.stderr)
        arguments = {"owner": args.owner, "repo": args.repo, "title": title, "body": body}
        if labels:
            arguments["labels"] = labels
        out = tool_call(url, "github", "create_issue", arguments)
        res = out.get("result") or out
        num = res.get("number") if isinstance(res, dict) else None
        if out.get("success") and num is not None:
            created_numbers.append(int(num))
            print(f"  -> #{num}", file=sys.stderr)
        else:
            print(f"  FAILED: {out.get('error', out)}", file=sys.stderr)

    if args.assign_copilot and created_numbers:
        print("Assigning Copilot to created issues...", file=sys.stderr)
        for num in sorted(created_numbers):
            out = tool_call(url, "github", "assign_copilot_to_issue", {"owner": args.owner, "repo": args.repo, "issue_number": num})
            ok = out.get("success") or out.get("result")
            print(f"  #{num} assign_copilot: {'OK' if ok else out.get('error', 'fail')}", file=sys.stderr)

    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
