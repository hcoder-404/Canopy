# Hardening Review: Channel Membership Enforcement

**Scope:** `canopy/api/routes.py`, `canopy/core/channels.py`, `canopy/ui/routes.py`, `canopy/ui/templates/channels.html`
**Date:** 2026-02-19

---

## Findings

### Q1 — `GET /api/v1/channels/<channel_id>/messages`: membership check?

**Finding (pre-fix):** The underlying `ChannelManager.get_channel_messages()` in `channels.py` *does* check membership — it returns an empty list `[]` when the caller is not a member. However, the API route handler returned **HTTP 200 OK** with an empty message list rather than a 403. A non-member therefore received a success response indistinguishable from "channel has no messages", leaking channel existence.

**Fix applied:** Added an explicit `channel_manager.get_member_role()` pre-check in the route handler. Returns `403 You are not a member of this channel` before the messages query runs.

---

### Q2 — `GET /api/v1/channels` (list channels): do non-members see channels?

**Finding:** ✅ No issue. `ChannelManager.get_user_channels()` uses `INNER JOIN channel_members` so only channels the caller belongs to are returned. The API route and the UI `/channels` page both call this method.

---

### Q3 — P2P sync channel creation: is Device B's local owner auto-added?

**Finding:** ✅ No issue. `create_channel_from_sync()` distinguishes between open/public channels and targeted (private/confidential) channels:
- **Open/public:** all registered human users on the local instance are added as members automatically.
- **Private/confidential:** only users in the explicit `initial_members` list from the sync payload are added.

Both paths include a fallback that adds the provided `local_user_id` if no members were inserted, ensuring the local instance owner can read open channels that arrive via P2P.

---

### Q4 — `POST /api/v1/channels/<channel_id>/messages`: membership check before posting?

**Finding (pre-fix):** `ChannelManager.send_message()` in `channels.py` validates membership internally and returns `None` when the caller is not a member. The route handler returned **HTTP 500** (`"Failed to send message"`) for that case — an incorrect and misleading status that obscured the real reason for refusal.

**Fix applied:** Added an explicit `channel_manager.get_member_role()` pre-check in the route handler immediately after input validation. Returns `403 You are not a member of this channel` before `send_message()` is called.

---

### Q5 — Channel `DELETE` and `PATCH`: restricted to owners/admins?

**Finding:** ✅ No issue.
- `DELETE /api/v1/channels/<channel_id>` calls `delete_channel()` which calls `is_channel_admin()`. Returns `403` when the requester is not a channel admin.
- `PATCH /api/v1/channels/<channel_id>` calls `update_channel_privacy()` which checks `role == 'admin'` or the instance-owner override (`allow_admin`). Returns `403` when neither condition is met.

---

### Q6 — UI channel list (`channels.html`): all channels or only member channels?

**Finding:** ✅ No issue. The `/channels` UI route calls `channel_manager.get_user_channels(user_id)`, which filters by membership via `INNER JOIN channel_members`. The Jinja2 template only iterates over the `channels` variable passed from that query, so private channels the user has no membership in are never rendered.

---

### Q7 — `selectChannel()` / `bindChannelItemHandlers()`: access check before loading messages?

**Finding (pre-fix):** The UI AJAX endpoint `/ajax/channel_messages/<channel_id>` contained a **self-heal** block that, when the current user was not a member of a public channel, automatically inserted a membership row and proceeded to return messages. This meant clicking any public channel in the UI — even one the user had never joined — would silently grant membership and expose all messages.

**Fix applied:** Removed the auto-add self-heal block entirely. The endpoint now calls `channel_manager.get_member_role()` at the top of the handler and returns `403` immediately if the user is not a member.

---

### Additional gap: `GET /api/v1/channels/<channel_id>/members`

**Finding (pre-fix):** The `get_channel_members_api` route had **no membership check**. Any authenticated user could enumerate the full member list of any channel — including private and confidential channels they had never joined.

**Fix applied:** Added a `channel_manager.get_member_role()` pre-check. Returns `403 You are not a member of this channel` for non-members.

---

### Additional gap: `GET /api/v1/channels/<channel_id>/search` and `GET /ajax/channel_search/<channel_id>`

**Finding (pre-fix):** Both search endpoints delegated membership validation to the underlying `search_channel_messages()` method, which silently returns `[]` for non-members. Both routes returned **HTTP 200 OK** with empty results instead of 403.

**Fix applied:** Added `channel_manager.get_member_role()` pre-checks in both the API route and the UI AJAX route. Both now return `403` for non-members.

---

## Out-of-Scope / Not Fixed

- **Toggle-like endpoint** (`POST /channels/<channel_id>/messages/<message_id>/like`): calls into `interaction_manager` which does not verify channel membership. A non-member who knows a message ID could like it. This is a minor integrity issue (no data disclosure) and requires changes beyond the listed scope files — documented here for a follow-up PR.
- **Notification preference endpoint** (`PATCH /channels/<channel_id>/notifications`): no membership check. Low severity (only affects the caller's own notification row) but should be guarded in a follow-up.

---

## Security Summary

All high-severity membership-bypass gaps in the listed scope files have been fixed. No new dependencies were introduced. Changes are confined to guard clauses at route-handler entry points; no data-model or P2P protocol changes were made.
