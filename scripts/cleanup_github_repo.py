#!/usr/bin/env python3
"""
Remove unnecessary files from GitHub repo via MCP.
Run: python scripts/cleanup_github_repo.py [--dry-run]
"""
import json
import sys
from typing import Optional
from urllib.request import Request, urlopen

URL = "http://localhost:8000"
OWNER = "kwalus"
REPO = "Canopy"

# Files to remove (local/agent/IDE-specific - should never be on GitHub)
TO_REMOVE = [
    ".cursor/rules/canopy-dev-bot-posting.mdc",
    ".cursor/rules/github-deploy.mdc",
    ".cursorrules",
    "AGENT_NOTE_AVATAR_PILLOW_VARIANTS.md",
    "AGENT_NOTE_CANOPY_POSTING.md",
    "AGENT_NOTE_CHANNEL_AUTO_REFRESH.md",
    "AGENT_NOTE_CHANNEL_EXPIRY_EDIT_UI.md",
    "AGENT_NOTE_CHANNEL_TTL.md",
    "AGENT_NOTE_CONNECT.md",
    "AGENT_NOTE_FEED_EXPIRY_DROPDOWN_ZINDEX.md",
    "AGENT_NOTE_HOMIE_SETUP.md",
    "AGENT_NOTE_MACHINE_A_ACTIVE.md",
    "AGENT_NOTE_MACHINE_B.md",
    "AGENT_NOTE_MACHINE_B_TIMESTAMP_FIX.md",
    "AGENT_NOTE_MCP_MANAGER.md",
    "AGENT_NOTE_MENTIONS_SYSTEM.md",
    "AGENT_NOTE_MESH_LOG_REVIEW_SELF_PEER_SANITIZE.md",
    "AGENT_NOTE_MESH_STABILITY_CONNECTION_CHURN_FIX.md",
    "AGENT_NOTE_MESSAGE_FILE_SECURITY_REVIEW.md",
    "AGENT_NOTE_NO_EMOJIS_IN_SCRIPTS.md",
    "AGENT_NOTE_POST_EXPIRY_EDIT_AND_COMMENT_TTL.md",
    "AGENT_NOTE_POST_TTL_PLAN_AND_MIGRATION.md",
    "AGENT_REPLY_MACHINE_A.md",
    "API_KEY_SETUP.md",
    "GITHUB_PUSH_GUIDE_FOR_WINDOWS_AGENT.md",
]


def rpc_call(method: str, params: dict) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    req = Request(URL, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def tool_call(tool: str, arguments: dict) -> dict:
    res = rpc_call("tools/call", {"name": "call_tool", "arguments": {"server": "github", "tool": tool, "arguments": arguments}})
    txt = (res.get("result") or {}).get("content") or []
    if not txt or not isinstance(txt[0].get("text"), str):
        return {"success": False, "error": res.get("error") or "No content"}
    return json.loads(txt[0]["text"])


def get_file_sha(path: str) -> Optional[str]:
    out = tool_call("get_file_sha", {"owner": OWNER, "repo": REPO, "path": path})
    if out.get("success") and out.get("result"):
        r = out["result"]
        return r.get("sha") if isinstance(r, dict) else None
    return None


def delete_file(path: str, sha: str) -> bool:
    out = tool_call("delete_file", {"owner": OWNER, "repo": REPO, "path": path, "sha": sha, "message": f"Remove {path} (local/agent file)"})
    return out.get("success", False)


def main():
    dry_run = "--dry-run" in sys.argv
    force = "--yes" in sys.argv or "-y" in sys.argv
    print("Files to remove from GitHub (local/agent/IDE-specific):\n")
    for path in TO_REMOVE:
        print(f"  {path}")
    print(f"\nTotal: {len(TO_REMOVE)} files")
    if dry_run:
        print("\n[DRY RUN] No changes made. Run without --dry-run to remove.")
        return 0

    if not force:
        print("\nProceed? (y/n): ", end="")
        if input().strip().lower() != "y":
            print("Aborted.")
            return 0

    ok = 0
    fail = 0
    for path in TO_REMOVE:
        sha = get_file_sha(path)
        if not sha:
            print(f"  SKIP {path} (not found or no sha)")
            fail += 1
            continue
        if delete_file(path, sha):
            print(f"  OK   {path}")
            ok += 1
        else:
            print(f"  FAIL {path}")
            fail += 1
    print(f"\nRemoved: {ok}, Failed: {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
