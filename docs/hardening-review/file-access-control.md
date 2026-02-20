# Hardening Review: File Access Control — Cross-Peer Download / Upload Permissions

**Date:** 2026-02-19  
**Scope files reviewed:**
- `canopy/security/file_access.py`
- `canopy/api/routes.py`
- `canopy/security/file_validation.py`
- `canopy/core/files.py`

---

## Findings and Answers to Specific Questions

### 1. Cross-device `evaluate_file_access` trace (Device A uploads, Device B reads)

**Channel-scoped check (channel_messages → channel_members):**
Device B queries its *local* database.  If the channel message was synced to
Device B (e.g. via P2P broadcast), the `channel_messages` row exists; the
function then checks `channel_members` for the requesting user.  If Device B
has not yet received the membership sync for the viewing user, `member` is
`None`, `can_view = False`, and the evidence is recorded but access is denied.
The function does **not** fall through to allow — it only returns `True` when
a positive membership row is present.

**Feed-post-scoped check (feed_posts → feed_manager.can_view):**
If Device B has the `feed_posts` row (synced via P2P) but `feed_manager` is
`None` or `feed_manager.get_post` raises an exception, `can_view` is set to
`False` explicitly.  Access is denied.  If Device B has no `feed_posts` row,
the query returns no rows, no evidence is collected, and the function returns
`unreferenced` (denied).

**Fallback when neither check passes:**
All return paths at the bottom of `evaluate_file_access` produce
`allowed=False`.  There is no accidental default-allow.  See fix §A below.

---

### 2. Default-allow risk when file metadata is missing

**Before this PR:** If `db_manager=None` was passed (e.g. due to an
application-startup race condition), the function would raise
`AttributeError` inside the `try` block, catch it, and return
`FileAccessResult(False, 'lookup-error')` — still a denial, but reliant on
exception handling rather than an explicit guard.

**After this PR (fix §A):** An explicit early-return
`FileAccessResult(False, 'missing-db')` is added before the DB queries.  The
function can never silently grant access when the database layer is
unavailable.

If the `files` table has no record for a given `file_id`, the function still
proceeds to the reference-lookup queries.  If no channel/feed/DM rows
reference it, `evidences` is empty and the function returns `unreferenced`
(denied).  No default-allow exists.

---

### 3. `DELETE /api/v1/files/<file_id>` — cross-user deletion

**Before this PR:** There was **no** `DELETE /api/v1/files/<file_id>` API
route.  File deletion was only triggered indirectly when the owning user
deleted a message or feed post that referenced the file.  The underlying
`FileManager.delete_file` method had an owner check but no way to invoke it
directly via the API.

**After this PR (fix §B):** A `DELETE /api/v1/files/<file_id>` endpoint
(requiring `DELETE_DATA` permission) is added.  Ownership is enforced at the
route level *before* calling `delete_file`:

```
if file_info.uploaded_by != caller_id and not is_admin:
    return 403
```

The `is_admin` flag is derived exclusively from the local
`db_manager.get_instance_owner_user_id()` — it is **never** sourced from the
HTTP request or a remote peer claim.  A user from Device B can therefore not
delete a file uploaded on Device A by claiming admin status.

`FileManager.delete_file` was also updated to accept an `is_admin` parameter
with the same semantics, replacing the previous TODO comment.

---

### 4. Upload quota gap — FINDING (out of scope for this PR)

**Finding:** Neither `POST /api/v1/files/upload` nor `FileManager.save_file`
enforces a per-user or per-instance cumulative disk-usage quota.  The only
size limit is a per-file cap (`MAX_FILE_SIZE`, default 100 MB from
`current_app.config`).

**Risk:** A single authenticated user (or a compromised API key) can exhaust
disk space by uploading many files each just under the per-file limit.  In a
multi-user or LAN deployment this is a meaningful denial-of-service vector.

**Recommendation (future PR):**
- Add a `SELECT SUM(size) FROM files WHERE uploaded_by = ?` check in
  `save_file` and reject the upload when the user would exceed a configurable
  `MAX_USER_STORAGE_BYTES` quota.
- Optionally add a global `MAX_INSTANCE_STORAGE_BYTES` guard.
- Surface quota information in the API response for clients.

This feature requires a new config key and additional DB reads on every
upload; it is clearly scoped as a separate, independently testable PR.

---

### 5. Server-side MIME validation on upload

`validate_file_upload` (from `canopy/security/file_validation.py`) is called
**before** `file_manager.save_file` in `POST /api/v1/files/upload`.  The
checks performed are:
1. MIME type against an allowlist (`ALLOWED_TYPES`).
2. Magic-bytes verification for all binary types.
3. Filename extension must match the normalised MIME type.
4. Zip-bomb detection for archive types.
5. Dangerous-content pattern scan for SVG and HTML.

Client-supplied MIME types are normalised (aliases resolved, generic
`application/octet-stream` inferred from extension).  The *validated* type —
not the client-supplied type — is stored.  Server-side validation is always
enforced.

---

### 6. P2P audio file transfer — binary vs. metadata reference

**Finding (documentation only):** When a channel message with an audio
attachment is broadcast to P2P peers, only the **metadata** (message JSON,
including the `file_id` reference) is transmitted via the P2P layer.  The
binary file content is **not** pushed to peers.

A peer that receives the message reference but does not yet have the file will
see a broken/missing attachment until it fetches the binary.  Currently there
is no automatic peer-to-peer file-fetch mechanism: the peer device must call
`GET /api/v1/files/<file_id>` (or the UI `GET /files/<file_id>` route) on the
**originating device** over the LAN to retrieve the binary.

This means:
- If the originating device is offline, the file is inaccessible to peers.
- `evaluate_file_access` on the peer will check the peer's *local* DB; if the
  `channel_members` row has been synced, access is granted and the peer can
  fetch the file from the origin device's HTTP endpoint.
- If `channel_members` has **not** synced yet, access is correctly denied
  until membership data arrives.

**Recommendation (future work, out of scope):** Implement an on-demand
file-fetch protocol where peers pull file binaries lazily when first
referenced, caching locally.  Until then, document to users that cross-device
file availability depends on both peers being online simultaneously.

---

## Changes Made in This PR

| File | Change |
|------|--------|
| `canopy/security/file_access.py` | Added explicit `db_manager is None` guard (fix §A); added deny-by-default comment at fallback |
| `canopy/core/files.py` | `delete_file` accepts `is_admin` parameter; updated ownership check |
| `canopy/api/routes.py` | Added `DELETE /api/v1/files/<file_id>` endpoint with owner + local-admin check (fix §B) |
| `docs/hardening-review/file-access-control.md` | This findings report |
