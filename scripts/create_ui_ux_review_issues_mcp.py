#!/usr/bin/env python3
"""
Create targeted UI/UX Copilot review issues via MCP Manager.

Scope: front-end only (templates, static JS/CSS, UI routes).
Constraint: incremental improvements to what exists — no redesigns, no backend changes.

Usage:
  python scripts/create_ui_ux_review_issues_mcp.py
  python scripts/create_ui_ux_review_issues_mcp.py --dry-run
  python scripts/create_ui_ux_review_issues_mcp.py --assign-copilot
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

REVIEW_LABEL = "copilot-review"

# Ground rules injected into every issue so Copilot stays on rails
GROUND_RULES = """
**Ground rules (read before starting):**
- Work only within the files listed under "Scope" below.
- Do NOT change API endpoints, database schema, P2P logic, or Python business logic.
- Do NOT redesign or restructure pages — improve what is already there.
- Keep every change small, self-contained, and non-breaking.
- If you find something that needs a larger fix, report it in a comment rather than changing it.
- Deliverable: a PR with focused fixes + a short markdown findings report as `docs/ux-review/<slug>.md`.
"""

UI_UX_REVIEW_TASKS = [
    {
        "title": "[Copilot UX Review] Navigation clarity and sidebar information architecture",
        "body": f"""**What to review:** The main sidebar navigation across all pages.

{GROUND_RULES}

**Scope (files only):**
- `canopy/ui/templates/base.html` — sidebar nav, mobile collapse, active-state highlighting
- `canopy/ui/static/js/canopy-main.js` — nav interaction logic
- `canopy/ui/templates/dashboard.html`

**Specific questions to answer:**
1. Is the active page clearly highlighted in the nav? On all themes?
2. Are nav labels descriptive enough that a new user knows where to go?
3. Is the sidebar collapse/expand behaviour on mobile smooth and recoverable?
4. Are there orphaned nav links that lead to empty or broken pages?
5. Do all nav icons have accessible `aria-label` or `title` attributes?

**Fix only:** small label text, aria labels, active-state CSS, mobile touch target sizes.
Report anything larger as a finding, not a code change.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot UX Review] Feed post creation and rich content rendering",
        "body": f"""**What to review:** The feed post composer and how posts render (text, links, images, embeds).

{GROUND_RULES}

**Scope (files only):**
- `canopy/ui/templates/feed.html`
- `canopy/ui/templates/dashboard.html` (feed section)
- `canopy/ui/static/js/canopy-main.js` — `renderRichContent()`, post submission, character counter

**Specific questions to answer:**
1. Is the post character limit clearly indicated before the user hits it?
2. Do image/audio/video attachments have clear upload progress or failure messages?
3. Does `renderRichContent()` handle edge cases cleanly (empty post, only whitespace, broken URL)?
4. Are YouTube embeds and inline images constrained to the column width on all themes?
5. Is there a clear "post sent" confirmation, or does the composer just clear silently?
6. Can a user easily delete or edit their own post from the UI?

**Fix only:** feedback text, CSS overflow/width constraints, null-check guards in JS.
Report architectural issues (e.g. no edit endpoint) as findings.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot UX Review] Channel messaging — composer, mentions, and message list",
        "body": f"""**What to review:** The channel messaging experience end to end.

{GROUND_RULES}

**Scope (files only):**
- `canopy/ui/templates/messages.html`
- `canopy/ui/templates/channels.html`
- `canopy/ui/static/js/canopy-main.js` — message send, polling, mention highlighting

**Specific questions to answer:**
1. Does the message composer submit cleanly on Enter (with Shift+Enter for newlines)?
2. Are @mention suggestions or autocomplete present? If not, is typing a mention at least highlighted after send?
3. Are unread message counts or indicators visible in the channel list?
4. Does the message list scroll to the bottom on new messages without jumping if the user has scrolled up?
5. Are long messages (>500 chars) truncated with a "show more" affordance, or do they overflow?
6. Is the send button disabled / spinner shown while a message is in flight?

**Fix only:** scroll behaviour, Enter-key handling, button disabled states, overflow CSS.
Report missing features (autocomplete, unread counts) as findings.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot UX Review] First-run onboarding, registration, and peer connect flow",
        "body": f"""**What to review:** The experience for a brand-new user from first launch through connecting to a peer.

{GROUND_RULES}

**Scope (files only):**
- `canopy/ui/templates/login.html`
- `canopy/ui/templates/settings.html` (invite / connect section)
- `canopy/ui/templates/profile.html`
- `canopy/ui/templates/dashboard.html` (empty state)
- `canopy/ui/routes.py` — registration and setup route logic (read-only for context; no changes)

**Specific questions to answer:**
1. Is there a clear empty state on the dashboard when no peers are connected yet?
2. Is the "connect to a peer" / invite flow discoverable from the UI (not just docs)?
3. Does the registration form give inline validation feedback (password strength, username taken)?
4. Are error messages from the server shown in the UI, or do they fail silently?
5. Is there a logical "next step" CTA after registration (e.g. "Set up your profile → Connect to a peer")?

**Fix only:** empty-state copy/illustration, inline form validation messages, CTA links.
Report missing flows as findings.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot UX Review] Forms, loading states, and error feedback across all pages",
        "body": f"""**What to review:** Every form and async action in the UI for consistent feedback.

{GROUND_RULES}

**Scope (files only):**
- All templates under `canopy/ui/templates/`
- `canopy/ui/static/js/canopy-main.js` — AJAX helpers, form submit handlers

**Specific questions to answer:**
1. Do all form submit buttons show a loading/disabled state during async calls?
2. Are server errors (4xx / 5xx) surfaced to the user with a human-readable message?
3. Are success confirmations consistent (toast, inline banner, or modal — pick one pattern)?
4. Do forms restore user input after a soft failure, or is the content lost on error?
5. Is there a consistent CSS class / pattern for error messages (e.g. `.alert-danger`), or are they ad-hoc?
6. Do any modals or dialogs trap focus correctly (Tab cycles within the modal)?

**Fix only:** consistent loading spinner classes, `disabled` attribute on buttons during fetch, error display consolidation.
Report UX patterns that need a broader audit as findings.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot UX Review] Theme consistency — all themes on all pages",
        "body": f"""**What to review:** Visual consistency of the dark, liquid-glass, eco, and default light themes.

{GROUND_RULES}

**Scope (files only):**
- `canopy/ui/templates/base.html` — CSS custom properties and theme `[data-theme]` selectors
- `canopy/ui/static/js/canopy-main.js` — theme switching logic
- All templates under `canopy/ui/templates/` — spot-check hardcoded colours

**Specific questions to answer:**
1. Are there any hardcoded `color:`, `background-color:`, or Bootstrap utility classes (e.g. `text-dark`, `bg-white`) that ignore the active theme?
2. Do cards, modals, dropdowns, and form inputs all respect `[data-theme]` overrides?
3. Is text contrast WCAG AA compliant on every theme? (Check especially grey helper text.)
4. Does the theme preference persist on page reload and propagate correctly?
5. Are there any components that look obviously broken in one specific theme?

**Fix only:** replace hardcoded colours with CSS variables, add missing `[data-theme]` overrides.
Do NOT change the theme system architecture.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot UX Review] Responsive layout and mobile usability",
        "body": f"""**What to review:** Layout correctness and usability at narrow viewports (≤ 768 px).

{GROUND_RULES}

**Scope (files only):**
- `canopy/ui/templates/base.html` — sidebar, top bar, breakpoints
- `canopy/ui/templates/feed.html`, `messages.html`, `channels.html`, `dashboard.html`
- `canopy/ui/static/js/canopy-main.js` — responsive JS (sidebar toggle, mini player)

**Specific questions to answer:**
1. Do any tables, code blocks, or media items overflow the viewport horizontally?
2. Are touch targets (buttons, links) at least 44×44 px on mobile?
3. Is the sidebar fully hidden (not partially visible) when collapsed on narrow viewports?
4. Does the mini player overlap important content on small screens?
5. Are the feed post composer and message input usable on mobile (keyboard doesn't cover input)?
6. Does the profile and settings page stack into a readable single column below 768 px?

**Fix only:** `max-width: 100%` on overflow elements, touch target sizing, sidebar z-index, mini player mobile offset.
Report major layout regressions as findings, not large-scale CSS refactors.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Copilot UX Review] Profile page and settings — completeness and clarity",
        "body": f"""**What to review:** The profile edit and settings pages for clarity, completeness, and flow.

{GROUND_RULES}

**Scope (files only):**
- `canopy/ui/templates/profile.html`
- `canopy/ui/templates/settings.html`
- `canopy/ui/templates/api_keys.html`
- `canopy/ui/routes.py` — profile and settings routes (read-only for context)

**Specific questions to answer:**
1. Is it obvious what fields are editable vs read-only on the profile page?
2. Is avatar upload drag-and-drop or click-to-upload? Is the affordance clear?
3. After saving profile changes, is there a clear success message?
4. Are the settings sections well-labelled and logically grouped?
5. Is the API keys page understandable to a non-developer user? (e.g. what is a key for, how to revoke)
6. Does the bio/display name update propagate visually within the same page session?

**Fix only:** field labels, help text, success/error messages, grouping via headings.
Report missing features as findings.""",
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
    ap = argparse.ArgumentParser(description="Create focused UI/UX Copilot review issues via MCP Manager")
    ap.add_argument("--owner", default="kwalus", help="GitHub repo owner")
    ap.add_argument("--repo", default="Canopy", help="GitHub repo name")
    ap.add_argument("--mcp-url", default="http://localhost:8000", help="MCP Manager URL")
    ap.add_argument("--dry-run", action="store_true", help="Print titles/bodies only")
    ap.add_argument("--no-labels", action="store_true", help="Skip label assignment")
    ap.add_argument("--assign-copilot", action="store_true", help="Assign Copilot to each created issue")
    args = ap.parse_args()
    url = args.mcp_url.rstrip("/")

    if args.no_labels:
        for t in UI_UX_REVIEW_TASKS:
            t["labels"] = []

    if args.dry_run:
        for i, task in enumerate(UI_UX_REVIEW_TASKS, 1):
            print(f"--- Issue {i}: {task['title']} ---")
            print(task["body"][:500] + "..." if len(task["body"]) > 500 else task["body"])
            print()
        print(f"Total: {len(UI_UX_REVIEW_TASKS)} issues.")
        return 0

    created_numbers = []
    for i, task in enumerate(UI_UX_REVIEW_TASKS, 1):
        title = task["title"]
        body = task["body"]
        labels = task.get("labels") or []
        print(f"[{i}/{len(UI_UX_REVIEW_TASKS)}] Creating: {title[:70]}...", file=sys.stderr)
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
            out = tool_call(url, "github", "assign_copilot_to_issue", {
                "owner": args.owner, "repo": args.repo, "issue_number": num
            })
            ok = out.get("success") or out.get("result")
            print(f"  #{num} assign_copilot: {'OK' if ok else out.get('error', 'fail')}", file=sys.stderr)

    print(f"Done. Created {len(created_numbers)}/{len(UI_UX_REVIEW_TASKS)} issues.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
