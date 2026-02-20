# Launch Hardening Review: Dead UI, Stub Routes, and Half-Finished Flows

**Scope:** `canopy/ui/templates/`, `canopy/ui/routes.py`, `canopy/api/routes.py`,
`canopy/ui/static/js/canopy-main.js`

**Status key:** ✅ working · ⚠️ gap/partial · 🐛 bug (fixed in this PR) · 📋 out-of-scope

---

## Q1 — Buttons / links that trigger a 404 or 501

No navigation links in `base.html` or the reviewed templates resolve to a missing
`@ui.route`. Every `url_for()` call in the nav-bar and the page templates maps to
a registered route.

**One bug found and fixed (see §3 below):** `trust.html` line 852 called
`/api/v1/delete-signals` (requires API-key auth) from the session-authenticated UI.
The call returned **401 Unauthorized** at runtime. Fixed by adding the UI AJAX
wrapper `/ajax/trust/delete_signal`.

---

## Q2 — API endpoints that are never called from UI or MCP (potential dead code)

| Endpoint | Status | Notes |
|---|---|---|
| `GET /api/v1/feed/search` | ⚠️ gap | Only surfaced through the feed page's own `?search=` query string (which calls `feed_manager.search_posts` directly). The API route is never called from the browser UI. Available to MCP clients. |
| `GET /api/v1/search` | ⚠️ gap | `SearchManager`-backed multi-type search. No UI page or button points to it. Available to MCP clients via API key. |
| `GET /api/v1/messages/search` | ⚠️ gap | Only reachable via MCP/API key; the messages page uses `/ajax/get_messages?search=`. |
| `POST /api/v1/database/backup`, `POST /api/v1/database/cleanup`, `GET /api/v1/database/export` | ⚠️ gap | No UI entry point. Admin page does not surface these. Available via API key only. |
| `GET /api/v1/agents/me/inbox/audit` | ⚠️ gap | No UI surface. Available via API key. |
| `POST /api/v1/agents/me/inbox/rebuild` | ⚠️ gap | No UI surface. Available via API key. |
| `GET /api/v1/handoffs`, `GET /api/v1/handoffs/<id>` | ⚠️ gap | No UI page. Available via API key. |

These endpoints are **not dead code** — they are reachable through MCP clients — but
they have no browser-UI entry point. A future PR could add an admin panel section for
database operations and a search page.

---

## Q3 — Trust page: add / edit / remove trust scores

| Action | Status |
|---|---|
| View trust tiers | ✅ Fully working |
| Change peer tier (drag-and-drop or select) | ✅ Calls `POST /trust/update` (session auth) |
| Send a delete signal | 🐛 **Fixed in this PR** — was calling `/api/v1/delete-signals` (API key required); now calls `/ajax/trust/delete_signal` (session auth) |
| Remove a peer from trust tracking entirely | ⚠️ No UI button to remove a trust record completely. `trust_manager` has no `remove_trust_score` method (not a regression — this was never built). |

---

## Q4 — Channels page: unread message badges

| Item | Status |
|---|---|
| Badge HTML in `channels.html` | ✅ Present (`{% if channel.unread_count > 0 %}` at line 846) |
| `unread_count` computed | 🐛 **Fixed in this PR** — `get_user_channels` always returned `unread_count=0`. SQL now counts messages created after `cm.last_read_at`. |
| `last_read_at` updated on read | ✅ `channel_manager.mark_channel_read()` is called when a user opens a channel (AJAX endpoint `/ajax/channel_messages/<channel_id>` at `canopy/ui/routes.py:6495`). |

---

## Q5 — Search feature

| Content type | Endpoint | Status |
|---|---|---|
| Feed posts | `GET /feed?search=<q>` (UI) · `GET /api/v1/feed/search` (API) | ✅ Working |
| Channel messages | `GET /ajax/channel_search/<channel_id>` (UI) | ✅ Working (per-channel only; no global channel-message search) |
| Direct messages | `GET /messages?search=<q>` (UI) · `GET /api/v1/messages/search` (API) | ✅ Working |
| Files | ⚠️ No dedicated file-search endpoint or UI button. | Not indexed. |
| Multi-type global | `GET /api/v1/search` (API only) | ⚠️ No browser UI; MCP only. |

Global cross-content search has no browser UI entry point and no search page at
`/search`. A future PR should add a search page or navbar search bar that calls
`/api/v1/search` (with an API key) or a new session-auth wrapper.

---

## Q6 — Dashboard: real-time data vs placeholders

The `dashboard.html` template exists but the `/` route now **redirects** to
`/channels` (desktop) or `/feed` (mobile) based on a cookie preference and
User-Agent. The template is therefore unreachable in normal use.

The template renders real data from the database (`message_stats`, `api_keys`,
`trust_scores`, `recent_messages`) and is not purely static — but since the route
redirects, it is effectively dead UI.

📋 **Out of scope for this PR.** Removing or re-exposing the dashboard template
would require a larger UX decision (add a `/dashboard` nav item or delete the
template). Flagged for a follow-up PR.

---

## Q7 — Forms that POST to a missing or error route

All `<form method="POST">` elements in the template files point to registered
routes:

| Template | Action | Route exists? |
|---|---|---|
| `login.html` | `POST /login` | ✅ |
| `login.html` | `POST /register` | ✅ |
| `setup.html` | `POST /setup` | ✅ |
| `claim_admin.html` | `POST /claim-admin` | ✅ |

No broken form targets found.

---

## Q8 — Admin approval flow

| Step | Status |
|---|---|
| Pending users listed in `/admin` | ✅ Filtered with `status == 'pending_approval'` and a count badge |
| Approve button → `POST /ajax/admin/users/<id>/approve` | ✅ Sets status to `active` |
| Suspend button → `POST /ajax/admin/users/<id>/suspend` | ✅ Sets status to `suspended` |
| Delete user → `DELETE /ajax/admin/users/<id>` | ✅ Removes user record |
| Pending accounts blocked from API | ✅ `require_auth` returns 403 with `status: pending_approval` |

Admin approval is **fully implemented**.

---

## Changes made in this PR

1. **`canopy/ui/routes.py`** — Added `POST /ajax/trust/delete_signal` (session-auth
   wrapper) so the Trust page can send delete signals without an API key.

2. **`canopy/ui/templates/trust.html`** — Updated `sendDeleteSignal()` to call
   `/ajax/trust/delete_signal` instead of `/api/v1/delete-signals`.

3. **`canopy/core/channels.py`** — Fixed `get_user_channels` SQL to compute
   `unread_count` as the number of non-expired messages newer than `last_read_at`,
   and propagate the value into the returned `Channel` objects.

## Known gaps (out of scope for this PR)

- No global multi-content search UI page (`/search`).
- No browser UI for database backup/cleanup/export operations.
- No UI button to permanently remove a peer from trust tracking.
- `dashboard.html` template is unreachable (route redirects to channels/feed).
- File attachments are not indexed by any search backend.
