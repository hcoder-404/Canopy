# DM System Hardening Review

**Scope:** `canopy/api/routes.py` — `/messages` endpoints  
**Review date:** 2026-02-19  
**Status:** Fixed + Findings

---

## Gaps Fixed in This PR

### 1. P2P broadcast missing on DM send (`POST /messages`)

**Before:** `send_message` created and stored the message locally but never called
`p2p_manager.broadcast_direct_message`, so the recipient peer never received the
message over the mesh network.

**Fix:** After a successful local store, `broadcast_direct_message` is now called
for every DM with a non-null `recipient_id` (best-effort; P2P failure does not
prevent the `201` response or local storage).

---

### 2. Inbox notification missing on DM send (`POST /messages`)

**Before:** No `InboxManager.create_trigger` call was made when a DM arrived, so
the recipient's agent inbox was never notified of the new message.

**Fix:** `inbox_manager.create_trigger(trigger_type='dm', ...)` is now called for
every DM with a non-null `recipient_id`.  The call is best-effort (failure is
logged as a warning, not returned as an error).

**Companion change in `canopy/core/inbox.py`:** `DEFAULT_INBOX_CONFIG` and
`DEFAULT_AGENT_INBOX_CONFIG` now include `"dm"` in `allowed_trigger_types`
(previously `["mention"]` only).  Without this addition the trigger would be
silently rejected by the rate-limit / type-filter logic in `InboxManager.create_trigger`.

---

### 3. Attachment-only DMs rejected (`POST /messages`)

**Before:** `if not content: return 400` — a message with no text body but with
file attachments in `metadata.attachments` was unconditionally rejected.

**Fix:** Validation now matches the behaviour of `PATCH /messages/<id>`:
```
if not content and not has_attachments:
    return 400
```

---

### 4. Silent empty list for unknown peer (`GET /messages/conversation/<other_user_id>`)

**Before:** Querying a conversation with a non-existent `other_user_id` returned
`200 {"messages": [], "count": 0}`, masking typos and invalid IDs.

**Fix:** A `db_manager.get_user(other_user_id)` lookup is performed first; if the
user does not exist the endpoint returns `404 {"error": "User not found"}`.

---

### 5. No route for group DM threads (`GET /messages/conversation/group/<group_id>`)

**Before:** `MessageManager.get_group_conversation` existed in the core layer but
had no API endpoint; group DM threads were completely inaccessible over the REST API.

**Fix:** New route `GET /api/v1/messages/conversation/group/<group_id>` added,
delegating to the existing `get_group_conversation` method.

---

## Remaining Gaps (out of scope for this PR)

### R1. Read receipts not broadcast back to sender

`POST /messages/<id>/read` updates `read_at` in the local database but does **not**
send a P2P notification to the original sender's peer.  The sender has no way to
learn that their message was read without polling `GET /messages`.

**Recommended fix (separate PR):** After a successful `mark_message_read`, call a
new `p2p_manager.broadcast_read_receipt(message_id, reader_id, sender_id)` helper
(to be added to `canopy/network/manager.py`).  The receiving peer should update the
`delivered_at`/`read_at` fields on the stored copy.

---

### R2. Group DM multi-sender P2P delivery not implemented

`POST /messages` with `metadata.group_id` / `metadata.group_members` stores the
message locally and broadcasts to **one** `recipient_id`.  There is no fan-out to
the remaining group members over P2P.

**Recommended fix (separate PR):** Add fan-out logic in `send_message` (or a
dedicated `POST /messages/group` endpoint) that iterates `group_members` and calls
`broadcast_direct_message` for each member, or introduces a group-broadcast
primitive in the P2P layer.

---

### R3. Inbox `trusted_only` filter silently drops DMs from untrusted peers

`DEFAULT_INBOX_CONFIG.trusted_only = True` and `min_trust_score = 50`.  A DM from
a peer whose trust score is below 50 (or who has not yet been recorded in
`trust_scores`) will be silently rejected at the inbox layer, so the local user
agent never sees the notification even though the message was stored.

**Recommended fix:** Either lower `min_trust_score` for `trigger_type='dm'`
(DMs already require an explicit `recipient_id`, so they carry a stronger intent
signal than broadcast mentions), or expose a per-user config knob via
`PATCH /agents/me/inbox/config` that operators can tune.

---

### R4. No unread DM count endpoint

There is no dedicated endpoint analogous to `GET /agents/me/inbox/count` for DM
unread counts.  Clients must fetch the full message list and count locally.

**Recommended fix (separate PR):** Add `GET /messages/unread/count` that returns
`SELECT COUNT(*) FROM messages WHERE recipient_id = ? AND read_at IS NULL`.
