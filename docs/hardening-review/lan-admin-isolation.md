# Hardening Review: Cross-device LAN Admin Isolation

**Scope:** `canopy/api/routes.py`, `canopy/core/database.py`, `canopy/core/app.py`,
`canopy/security/file_access.py`

---

## Answers to Specific Questions

### Q1 — Can a Device B API key call `GET /api/v1/messages` and receive DMs synced from Device A?

**Finding:** Partially.  The `_on_p2p_direct_message` handler in `app.py` already guards
storage: it only stores an incoming DM if `recipient_id` is a real local user (not a
shadow/peer account, not absent).  So DMs addressed to Device A users are never stored on
Device B.

However, `MessageManager.get_messages` and `search_messages` in `canopy/core/messaging.py`
(out of scope) include the clause `OR m.recipient_id IS NULL`.  Any message with no
recipient (e.g., old broadcast-style records) is returned to every caller regardless of
sender.  Because `messaging.py` is outside the declared scope this has been documented
rather than modified.

**Status:** P2P DM storage is correctly scoped; the `recipient_id IS NULL` exposure is
documented below as a deferred finding.

---

### Q2 — Can a Device B API key access `GET /api/v1/files/<file_id>` for a file uploaded on Device A?

**Finding (before this PR):** Yes, for Device B's admin.  `evaluate_file_access` has an
`is_admin=True` shortcut that bypasses all content-scoped checks.  `is_admin` was derived
solely from `owner_id == viewer_user_id`, where `owner_id` is Device B's local instance
owner.  A file synced from Device A (uploaded by a shadow/peer user) would be returned to
Device B's admin unconditionally.

**Fix applied:** In both `GET /files/<file_id>` and `GET /files/<file_id>/access` the code
now checks whether `file_info.uploaded_by` belongs to a user with `origin_peer` set.  If
so, `is_admin` is forced to `False`, routing the request through the normal content-scoped
checks (channel membership, feed visibility, DM visibility).

---

### Q3 — Is the `instance_owner_id` admin check aware that Device B's admin ≠ Device A's admin?

**Finding:** Yes.  `get_instance_owner_user_id` reads from Device B's own `system_state`
table; it has no concept of Device A's admin.  Admin elevation therefore cannot cross
device boundaries by design.

**Hardening applied:** The last-resort fallback query previously had no filter against
shadow/peer usernames, meaning that in a pathological deployment where every real local
account was deleted it could promote a `peer-*` shadow account to instance owner.  A
`AND username NOT LIKE 'peer-%'` filter has been added.

---

### Q4 — Are feed posts and channel messages stored with a `peer_origin` marker that restricts admin actions?

**Finding:** Incoming P2P feed posts and channel messages do receive
`metadata["origin_peer"] = from_peer` when stored (set in `_on_p2p_feed_post` and the
channel-message handler in `app.py`).  However, no existing code prevented the local admin
from deleting a post that originated on a different device.

**Fix applied:** `DELETE /feed/posts/<post_id>` now checks `metadata["origin_peer"]`
against the local P2P peer ID before granting admin-level deletion.  If the post carries
an `origin_peer` from a different device, `allow_admin` is forced to `False`, restricting
deletion to the actual post author.

**Note:** Channel-message deletion is already author-only (no admin bypass exists in that
code path); no change was needed there.

---

### Q5 — Do any API endpoints return data from ALL users regardless of who is authenticated?

**Finding:** No listing endpoint for all users exists.  `GET /profile` returns only the
caller's own profile.  `GET /channels` returns only channels the caller is a member of.

One gap was identified: `GET /channels/<channel_id>/members` had no membership guard — any
authenticated user could enumerate the members of any channel (including private/confidential
ones) without being a member themselves.

**Fix applied:** `get_channel_members_api` now calls `channel_manager.get_member_role` and
returns HTTP 403 if the caller is not a member of the channel.

---

### Q6 — Does `GET /api/v1/channels/<channel_id>` (and related endpoints) properly scope to members?

**Finding:**
- `GET /channels/<channel_id>/messages` — **Correct.** `ChannelManager.get_channel_messages`
  queries `channel_members` before returning messages and returns an empty list for non-members.
- `GET /channels` — **Correct.** `get_user_channels` is scoped to the caller's memberships.
- `GET /channels/<channel_id>/members` — **Gap.**  No membership check (fixed in this PR).

---

## Deferred Findings (out-of-scope for this PR)

### DF-1: `recipient_id IS NULL` in `MessageManager` (messaging.py)

`get_messages()` and `search_messages()` both include `OR m.recipient_id IS NULL`.  Any
stored message without a recipient is returned to every authenticated caller.  This
predates P2P sync and likely exists for broadcast/system messages, but it is a potential
data-scoping gap if such records accumulate from peer traffic.

**Recommendation:** Remove `OR m.recipient_id IS NULL` from both queries in
`canopy/core/messaging.py`, or restrict it to `m.sender_id = ?` when `recipient_id IS
NULL`.

**Why deferred:** `messaging.py` is outside the declared scope for this PR.

### DF-2: Local admin can edit peer-origin feed posts via `update_post`

`update_feed_post` in `routes.py` correctly restricts editing to `post.author_id ==
caller`; there is no `allow_admin` path.  This gap is therefore already closed at the
routes layer.  No additional change needed.

### DF-3: No immutability enforcement for channel messages arriving from peers

`delete_channel_message` already restricts deletion to the message author (no admin bypass).
However, an admin with direct database access can still mutate synced channel messages.
This is an operational concern rather than an API concern and requires no API change.

### DF-4: `GET /device/profile` and `POST /device/profile` were unauthenticated

Both endpoints exposed/modified the local device display name and avatar without any API
key.  Fixed in this PR by adding `@require_auth()`.

---

## Summary of Code Changes

| File | Change |
|------|--------|
| `canopy/api/routes.py` | `get_channel_members_api` — 403 guard for non-members |
| `canopy/api/routes.py` | `delete_feed_post` — skip admin bypass for peer-origin posts |
| `canopy/api/routes.py` | `get_file_api` — skip admin bypass when uploader is a peer user |
| `canopy/api/routes.py` | `get_file_access_api` — same peer-uploader guard |
| `canopy/api/routes.py` | `get_device_profile_api` / `set_device_profile_api` — add `@require_auth()` |
| `canopy/core/database.py` | `get_instance_owner_user_id` — last-resort fallback excludes shadow users |
