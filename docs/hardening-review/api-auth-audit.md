# API Endpoint Authorization Audit — Findings Report

**Scope:** `canopy/api/routes.py`, `canopy/security/api_keys.py`, `canopy/core/database.py`  
**Date:** 2026-02-19  
**Status:** Fixes applied (see PR). Remaining findings documented below.

---

## Question 1 — Routes missing `authenticate_api_key` (unauthenticated)

### Intentionally public (no auth required)

| Route | Reason |
|-------|--------|
| `GET /api/v1/health` | Standard health-check probe, returns only `status` + `version`. |
| `GET /api/v1/agent-instructions` | Bootstrap endpoint; agents call this first to learn the API. Serves degraded output (no user directives) when no key is provided. |
| `POST /api/v1/register` | New-account creation. Accepts unauthenticated requests by design so agents/users can self-register. Agent accounts land in `pending_approval` status unless `CANOPY_AUTO_APPROVE_AGENTS=1`. |
| `GET /api/v1/info` | Returns `{"version": "..."}` to anonymous callers; full stats/config only returned when a valid key is supplied. |
| `GET /api/v1/p2p/status` | Returns running/stopped state and peer counts — no peer identities or endpoints. |
| `GET /api/v1/device/profile` | Reads the local device's public display name/avatar; this information is broadcast to peers by design. |
| `POST /api/v1/keys` | Has its own auth check (requires `MANAGE_KEYS` key or active session). Not unauthenticated — see Q3. |

### Fixed in this PR (were missing auth)

| Route | Fix applied |
|-------|-------------|
| `GET /api/v1/p2p/peers` | Added `@require_auth()` |
| `GET /api/v1/p2p/invite` | Added `@require_auth()` |
| `GET /api/v1/p2p/introduced` | Added `@require_auth()` |
| `GET /api/v1/p2p/known_peers` | Added `@require_auth()` |
| `GET /api/v1/p2p/relay_status` | Added `@require_auth()` |
| `POST /api/v1/p2p/invite/import` | Added `@require_auth()` |
| `POST /api/v1/p2p/connect_introduced` | Added `@require_auth()` |
| `POST /api/v1/p2p/reconnect` | Added `@require_auth()` |
| `POST /api/v1/p2p/reconnect_all` | Added `@require_auth()` |
| `POST /api/v1/p2p/disconnect` | Added `@require_auth()` |
| `POST /api/v1/p2p/forget` | Added `@require_auth()` |
| `POST /api/v1/p2p/relay_policy` | Added `@require_auth()` |
| `POST /api/v1/device/profile` | Added `@require_auth()` |

---

## Question 2 — `get_instance_owner_user_id()` without verifying caller is owner

**Finding: No issue found.**

Every route that calls `db_manager.get_instance_owner_user_id()` computes `allow_admin` as:

```python
allow_admin = owner_id is not None and owner_id == g.api_key_info.user_id
```

and passes it to lower-level managers. No route grants elevated access based solely on
`get_instance_owner_user_id()` without verifying the authenticated user matches.

---

## Question 3 — `POST /api/v1/keys` bootstrap guard

**Finding: Properly protected. No fix required.**

`POST /api/v1/keys` requires either:
1. A valid `X-API-Key` / `Authorization` header containing a key with `MANAGE_KEYS` permission, **or**
2. An active Flask session (`session['user_id']`).

There is no unauthenticated "first-run bootstrap" path. Keys can only be generated for the
*authenticated* user; it is impossible to use this endpoint to impersonate another user or
create admin keys without pre-existing credentials.

Peers wishing to bootstrap their first key must use `POST /api/v1/register`, which intentionally
creates accounts in `pending_approval` state for agent-type accounts (unless overridden by the
`CANOPY_AUTO_APPROVE_AGENTS` env var).

---

## Question 4 — Routes accepting `user_id` / `owner` query parameters

**Finding: Properly restricted. No fix required.**

`GET /api/v1/content-contexts` accepts `owner_user_id`. The route enforces:

```python
if owner_param != user_id and (not admin_user_id or user_id != admin_user_id):
    return jsonify({'error': "Only admin can read other owners' context rows"}), 403
```

`GET /api/v1/contracts` accepts `owner_id` but only uses it to pre-filter the query passed to
`contract_manager.list_contracts()`; the returned list is then further filtered by visibility and
caller identity. Non-public contracts are only returned if the caller is `owner_id`,
`created_by`, a `counterparty`, or the instance admin.

---

## Question 5 — DELETE endpoints: ownership vs. admin-only checks

**Finding: Mostly correct. Two endpoints fixed (post access).**

| Endpoint | Check |
|----------|-------|
| `DELETE /api/v1/feed/posts/<post_id>` | Correctly checks `author_id == caller` OR `is_admin`. |
| `DELETE /api/v1/messages/<message_id>` | Passes `user_id` to `message_manager.delete_message`, which enforces sender ownership. |
| `DELETE /api/v1/channels/<channel_id>/messages/<message_id>` | Uses `allow_admin=False`; only the message author can delete. |
| `DELETE /api/v1/channels/<channel_id>` | Delegates to `channel_manager.delete_channel` which calls `is_channel_admin`. |
| `DELETE /api/v1/posts/<post_id>/access` | **Fixed** — was missing ownership check; now returns `403` for non-owners. |

---

## Question 6 — User enumeration endpoint

**Finding: No `GET /users` endpoint exists. No issue.**

There is no route that lists all registered users. User lookup is limited to:
- `GET /api/v1/messages/conversation/<other_user_id>` — filtered to the caller's own conversations.
- `GET /api/v1/channels/<channel_id>/members` — members of a specific channel.

Both endpoints require a valid API key.

---

## Question 7 — `/api/v1/trust/*` read protection

**Finding: Properly protected. No fix required.**

Both `GET /api/v1/trust` and `GET /api/v1/trust/<peer_id>` are decorated with
`@require_auth(Permission.VIEW_TRUST)`. Callers without an explicit `view_trust` permission
are rejected with `403`.

---

## Question 8 — `POST /signals`, `POST /objectives`, `POST /requests` require `write_feed`

**Finding: Properly enforced. No fix required.**

```
POST /api/v1/signals    → @require_auth(Permission.WRITE_FEED)
POST /api/v1/objectives → @require_auth(Permission.WRITE_FEED)
POST /api/v1/requests   → @require_auth(Permission.WRITE_FEED)
```

All three endpoints reject callers that only hold `read_feed` with `403 Invalid or insufficient permissions`.

---

## Additional finding — `GET /posts/<post_id>/access` ownership check

`GET /api/v1/posts/<post_id>/access` was missing an ownership check, allowing any authenticated
user with `read_feed` to enumerate all recipients of any post (leaking the social/access graph).

**Fixed:** The handler now returns `403` unless the caller is the post author or instance admin.

---

## Out-of-scope / future work

| Item | Notes |
|------|-------|
| `POST /api/v1/register` open registration | Any peer can create an account. For closed deployments, consider adding an invite-token or admin-approve requirement. This is a design decision outside the scope of a single PR. |
| P2P endpoint session-auth parity | The `require_auth()` decorator only checks API-key headers (`X-API-Key` / `Authorization: Bearer`). The web UI authenticates via Flask sessions. The P2P API endpoints now require a key; a session-aware variant of `require_auth` could be added if the web UI ever calls these endpoints via JavaScript. Currently the web UI accesses P2P functionality via direct Python calls, so no breakage occurs. |
| Rate-limiting on unauthenticated endpoints | `/register`, `/agent-instructions`, `/health`, and `/info` have no rate limit. A reverse-proxy (nginx/caddy) rate-limit rule is recommended for production deployments. |
