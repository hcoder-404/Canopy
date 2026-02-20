#!/usr/bin/env python3
"""
Create launch-hardening Copilot review issues via MCP Manager.

Focus areas:
  1. Cross-device / LAN admin data isolation
  2. DM system end-to-end completeness
  3. API endpoint authorization consistency
  4. Feature completeness (stubs, dead UI, partial flows)
  5. File access control across peers
  6. Channel membership enforcement

Usage:
  python scripts/create_launch_hardening_issues_mcp.py
  python scripts/create_launch_hardening_issues_mcp.py --dry-run
  python scripts/create_launch_hardening_issues_mcp.py --assign-copilot
"""

import argparse
import json
import sys

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    Request, urlopen, HTTPError, URLError = None, None, None, None

REVIEW_LABEL = "launch-hardening"

GROUND_RULES = """
**Ground rules (read before starting):**
- Work only within the files listed under "Scope".
- Do NOT redesign data-models or change database migrations unless the issue explicitly says so.
- Do NOT change P2P network protocol framing or encryption.
- Keep every change minimal, auditable, and independently testable.
- If a gap requires a feature that is clearly out of scope for a single PR, report it in a
  `docs/hardening-review/<slug>.md` findings file and leave code untouched.
- Deliverable: a focused PR with fixes + `docs/hardening-review/<slug>.md` findings report.
- Prefer adding explicit `403` / `404` guards over silently returning empty data.
"""

HARDENING_TASKS = [
    {
        "title": "[Launch Hardening] Cross-device LAN admin isolation — data visible to peer nodes",
        "body": f"""**Problem statement:**
When two Canopy instances share a LAN and are P2P-connected, every node accumulates a local
copy of synced data (feed posts, channel messages, peer profiles). Each device has its own
`instance_owner_id` (admin). A user who holds an API key on Device B could potentially query
Device B's local database for data that was synced from Device A — including content that Device A's
users believe is private.

This issue asks Copilot to audit and harden the boundary between "locally owned" and "synced-from-peer" data.

{GROUND_RULES}

**Scope (files for investigation and fixes):**
- `canopy/api/routes.py` — all GET endpoints that return feed posts, channel messages, DMs, profiles, files
- `canopy/core/database.py` — `get_instance_owner_user_id`, peer_device_profiles table
- `canopy/core/app.py` — `_on_p2p_feed_post`, `_on_p2p_channel_message`, `_on_profile_sync`, `_on_p2p_direct_message`
- `canopy/security/file_access.py` — `evaluate_file_access`

**Specific questions to answer:**
1. Can a user authenticated on Device B (with a valid Device B API key) call `GET /api/v1/messages`
   and receive DMs that were synced from Device A? If so, is this intentional?
2. Can a Device B API key access `GET /api/v1/files/<file_id>` for a file uploaded on Device A,
   even if Device B's `evaluate_file_access` has no channel-membership record for that user?
3. Is the `instance_owner_id` admin check (in `get_instance_owner_user_id`) aware that the admin
   on Device B is a *different person* than the admin on Device A? Confirm admin elevation cannot
   cross device boundaries.
4. When feed posts and channel messages arrive via P2P, are they stored with a `peer_origin` marker
   that restricts what the local admin can do with them (e.g., delete, edit)?
5. Are there any API endpoints that return data from ALL users regardless of who is authenticated
   (e.g., `GET /api/v1/users` or profile search) without proper scoping?
6. Does `GET /api/v1/channels/<channel_id>/messages` check that the authenticated user is a member
   of that channel — including channels they joined only on a remote device?

**Fix:** Add per-request user-scoping guards where missing. Document any intentional data-sharing
decisions in the findings file so they can be reviewed before launch.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Launch Hardening] DM system completeness — send, receive, notify, read receipts, attachments",
        "body": f"""**Problem statement:**
The Direct Messages feature was implemented but its end-to-end completeness has not been validated.
Several sub-flows (inbox notifications for incoming DMs, read receipts, file attachments in DMs,
group DM multi-recipient delivery, P2P broadcast of DMs to the correct peer) need to be confirmed
as working or flagged as unimplemented.

{GROUND_RULES}

**Scope (files for investigation and fixes):**
- `canopy/api/routes.py` — `/messages` endpoints (POST, GET, PATCH, DELETE, /read, /search, /conversation/<id>)
- `canopy/core/app.py` — `_on_p2p_direct_message`, DM-related inbox trigger calls
- `canopy/core/inbox.py` — `record_mention_triggers`, `create_trigger` — check if DMs produce inbox items
- `canopy/ui/templates/messages.html` — read-receipt UI, unread badge, attachment display
- `canopy/ui/routes.py` — `/ajax/messages*` and `/ajax/send_message`

**Specific questions to answer:**
1. When a DM arrives via P2P (`_on_p2p_direct_message`), does it trigger an inbox item for the
   recipient? If not, how does the recipient know they have a new DM?
2. Does `POST /api/v1/messages/read/<message_id>` update a `read_at` column? Is that column present
   in the `messages` table schema? Does the UI show read vs unread state?
3. When a DM is sent with `file` attachments, does the file metadata survive the P2P broadcast to
   the recipient's device? Can the recipient download the file via `GET /api/v1/files/<id>`?
4. For group DMs (`recipient_ids` array), does each recipient receive the message — both locally
   and via P2P if they are on a different device?
5. Is the `PATCH /api/v1/messages/<id>` (edit) endpoint guarded so only the sender can edit?
6. Is the `DELETE /api/v1/messages/<id>` endpoint guarded so only the sender (or admin) can delete?
   Is there a P2P delete broadcast for DMs?
7. Does `GET /api/v1/messages/conversation/<other_user_id>` return messages from *both* sides of the
   conversation, sorted chronologically, including P2P-received messages?
8. Are there unread-DM counts visible anywhere in the UI (sidebar badge, dashboard widget)?

**Fix:** Add missing inbox triggers, fix auth guards on edit/delete, and add UI unread indicators
where absent. Document anything requiring a larger feature as a finding.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Launch Hardening] API endpoint authorization audit — missing auth, over-permissive routes",
        "body": f"""**Problem statement:**
As the API surface has grown rapidly, some endpoints may be missing auth checks, accepting
unauthenticated requests, or granting more data than the caller's permissions warrant.
This issue asks for a systematic walk-through of every route in `canopy/api/routes.py`.

{GROUND_RULES}

**Scope (files for investigation and fixes):**
- `canopy/api/routes.py` — every `@api.route(...)` decorator and handler
- `canopy/security/api_keys.py` — `authenticate_api_key`, permission list
- `canopy/core/database.py` — permission constants

**Specific questions to answer:**
1. List every `@api.route` that does **not** call `authenticate_api_key` (or equivalent) before
   touching user data. Which of these are intentionally public?
2. Are there any routes that call `db_manager.get_instance_owner_user_id()` and then grant
   elevated access without first verifying that the authenticated user *is* that owner?
3. Does `POST /api/v1/keys` (first-run admin key bootstrap) have a guard preventing it from being
   called after the first user is registered? If not, can any peer create an admin key?
4. Check all routes that accept a `user_id` or `owner` query parameter — do they restrict results
   to the authenticated user's data, or can any authenticated user query another user's data?
5. Do the `DELETE` endpoints (posts, messages, files, channels) consistently require either
   ownership or admin? Look for any that only check `allow_admin` without also checking ownership.
6. Is the `GET /api/v1/users` or any user-enumeration endpoint restricted so peers cannot harvest
   the full user list?
7. Are the `/api/v1/trust/*` endpoints read-protected? (Trust scores could reveal social graph info.)
8. Confirm all `POST /api/v1/signals`, `POST /api/v1/objectives`, `POST /api/v1/requests` require
   the `write_feed` permission and reject callers with only `read_feed`.

**Fix:** Add missing `authenticate_api_key` calls, tighten `allow_admin` checks, add permission
assertions where missing. Document any intentional public routes.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Launch Hardening] Feature completeness audit — dead UI, stub routes, and half-finished flows",
        "body": f"""**Problem statement:**
Several features were partially implemented during rapid development and may have UI elements
pointing to non-functional endpoints, or API endpoints with no UI entry point. Before launch
these gaps need to be catalogued and the most critical ones closed.

{GROUND_RULES}

**Scope (files for investigation):**
- All templates under `canopy/ui/templates/`
- `canopy/ui/routes.py` — every `@ui.route`
- `canopy/api/routes.py` — look for routes that return `501`, `{{"error": "not implemented"}}`, or
  have empty bodies
- `canopy/ui/static/js/canopy-main.js` — look for button `onclick` handlers that call undefined
  functions or are `// TODO`

**Specific questions to answer:**
1. Are there any buttons, links, or menu items in the UI that trigger a `404` or `501` when clicked?
   List them by template file and line number.
2. Are there any API endpoints in `routes.py` that exist but are never called from the UI or MCP
   (potential dead code)?
3. Does the **Trust** page (`/trust`) fully work — can the user add, edit, and remove trust
   scores for peers, and do those changes persist?
4. Does the **Channels** page show unread message counts or "new message" badges for channels
   with activity since last visit? If not, is the data available but just not surfaced?
5. Is the **Search** feature (`/search` or `/ajax/search`) connected to a working backend? Are
   all content types (feed posts, channel messages, DMs, files) indexed?
6. Does the **Dashboard** show meaningful real-time data (recent activity, connected peers,
   pending inbox items), or is it mostly static placeholders?
7. Are there any `<form>` elements that POST to a route which doesn't exist or returns an error?
8. Is the **admin approval** flow (if `pending_approval` users exist) fully implemented — can the
   admin approve/reject users from the UI?

**Fix:** Wire up the highest-priority dead UI elements, add `501 Not Implemented` responses
to clearly stubbed routes, and document the gaps in the findings file.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Launch Hardening] File access control — cross-peer download and upload permissions",
        "body": f"""**Problem statement:**
Files are central to Canopy's use (audio clips, images, attachments). The access control
model (channel membership, feed post authorship, DM visibility) needs to be verified as
airtight, especially in the cross-device LAN scenario where Device B may have a local copy
of a file reference but the `channel_members` table has no record for the requesting user.

{GROUND_RULES}

**Scope (files for investigation and fixes):**
- `canopy/security/file_access.py` — `evaluate_file_access`, all evidence checks
- `canopy/api/routes.py` — `GET /api/v1/files/<file_id>`, `POST /api/v1/files/upload`,
  `GET /api/v1/files/<file_id>/access`, `DELETE /api/v1/files/<file_id>`
- `canopy/security/file_validation.py` — upload validation
- `canopy/core/files.py` — file storage, metadata

**Specific questions to answer:**
1. Walk through `evaluate_file_access` for a file uploaded on Device A and accessed from Device B:
   - Does Device B have the `channel_members` row needed to pass the channel-scoped check?
   - Does Device B have the `feed_posts` row for a feed-post-scoped file?
   - If neither check passes, does the access correctly deny or does it fall through to a default-allow?
2. Is there a case where `evaluate_file_access` returns `allowed=True` by default (e.g., if the
   file metadata is missing or the DB has no record of the file)?
3. Can an authenticated user on Device B call `DELETE /api/v1/files/<file_id>` for a file
   uploaded by a different user on Device A? Is admin-only deletion scoped to the local instance?
4. Does `POST /api/v1/files/upload` enforce a per-user or per-instance file size quota?
   Is there a hard cap on total disk usage?
5. Are file MIME types validated server-side on upload, or only on the client? (Confirm
   `file_validation.py` is always invoked before storage.)
6. For audio files attached to a channel message and then broadcast via P2P — does the file
   binary transfer to the peer, or only the metadata reference? If only the reference, how does
   the peer download the file?

**Fix:** Harden the fallback path in `evaluate_file_access` to deny-by-default when evidence
is ambiguous. Add owner check to DELETE. Document quota gap as a finding.""",
        "labels": [REVIEW_LABEL],
    },
    {
        "title": "[Launch Hardening] Channel membership enforcement — consistent access checks across all endpoints",
        "body": f"""**Problem statement:**
Channel membership is the primary access-control primitive for channel messages, files, and
mentions. If any endpoint reads channel data without first checking membership, a user could
access a private channel they haven't joined — especially after P2P sync stores the channel
on their local device.

{GROUND_RULES}

**Scope (files for investigation and fixes):**
- `canopy/api/routes.py` — all `/channels/...` endpoints
- `canopy/core/channels.py` — `get_channel_messages`, `create_channel_message`, `get_channel_members_list`
- `canopy/ui/routes.py` — `/ajax/channel_messages/<channel_id>`, channel list rendering
- `canopy/ui/templates/channels.html` — client-side channel switching, what is rendered

**Specific questions to answer:**
1. Does `GET /api/v1/channels/<channel_id>/messages` verify channel membership before returning
   messages? Check both the API route handler *and* the underlying `channels.py` function.
2. Can an authenticated user call `GET /api/v1/channels` (list channels) and see channels they
   are not a member of? What about private/invite-only channels?
3. When a new channel is created via P2P sync on Device B, is the local instance owner (Device B)
   automatically added as a member, or do they have no membership and thus cannot read it?
4. Does `POST /api/v1/channels/<channel_id>/messages` (send a message) check membership before
   accepting the message, or can any authenticated user post to any channel?
5. Are channel `DELETE` and `PATCH` (edit/rename) operations restricted to channel owners or
   instance admins?
6. Does the UI channel list (`channels.html`) render *all* channels from the DB, or only channels
   the authenticated user is a member of? Check both the Jinja2 template and the AJAX call.
7. When `bindChannelItemHandlers()` fires and `selectChannel(channelId)` is called, does it verify
   the user has access before loading messages, or could it load messages for a channel the user
   shouldn't see?

**Fix:** Add explicit membership checks in all channel read endpoints. Ensure channel list
endpoint filters by caller's membership. Document any intentional "open channel" design.""",
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
    ap = argparse.ArgumentParser(description="Create launch-hardening Copilot review issues via MCP Manager")
    ap.add_argument("--owner", default="kwalus", help="GitHub repo owner")
    ap.add_argument("--repo", default="Canopy", help="GitHub repo name")
    ap.add_argument("--mcp-url", default="http://localhost:8000", help="MCP Manager URL")
    ap.add_argument("--dry-run", action="store_true", help="Print titles/bodies only, no network calls")
    ap.add_argument("--no-labels", action="store_true", help="Skip label assignment")
    ap.add_argument("--assign-copilot", action="store_true", help="Assign Copilot to each created issue")
    args = ap.parse_args()
    url = args.mcp_url.rstrip("/")

    if args.no_labels:
        for t in HARDENING_TASKS:
            t["labels"] = []

    if args.dry_run:
        for i, task in enumerate(HARDENING_TASKS, 1):
            print(f"--- Issue {i}: {task['title']} ---")
            print(task["body"][:600] + "..." if len(task["body"]) > 600 else task["body"])
            print()
        print(f"Total: {len(HARDENING_TASKS)} issues.")
        return 0

    created_numbers = []
    for i, task in enumerate(HARDENING_TASKS, 1):
        title = task["title"]
        body = task["body"]
        labels = task.get("labels") or []
        print(f"[{i}/{len(HARDENING_TASKS)}] Creating: {title[:70]}...", file=sys.stderr)
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
            # Some MCP wrappers return the number at top-level even on "success: False"
            if isinstance(res, dict) and isinstance(res.get("number"), int):
                created_numbers.append(int(res["number"]))
                print(f"  -> #{res['number']} (via result fallback)", file=sys.stderr)
            else:
                print(f"  FAILED: {out.get('error', out)}", file=sys.stderr)

    if args.assign_copilot and created_numbers:
        print("\nAssigning Copilot to created issues...", file=sys.stderr)
        for num in sorted(created_numbers):
            out = tool_call(url, "github", "assign_copilot_to_issue", {
                "owner": args.owner,
                "repo": args.repo,
                "issue_number": num,
                "base_branch": "main",
                "custom_instructions": (
                    "You are performing a targeted security and completeness review. "
                    "Read the issue carefully. Follow ALL ground rules: stay within the "
                    "listed scope files, make minimal changes, and write a findings report "
                    "at docs/hardening-review/<slug>.md documenting everything you found "
                    "that is out of scope to fix in this PR. "
                    "Prioritise correctness and safety over elegance."
                ),
            })
            ok = out.get("success") or (out.get("result") and "error" not in str(out.get("result", "")))
            print(f"  #{num} assign_copilot: {'OK' if ok else out.get('error', 'fail')}", file=sys.stderr)

    print(f"\nDone. Created {len(created_numbers)}/{len(HARDENING_TASKS)} issues.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
