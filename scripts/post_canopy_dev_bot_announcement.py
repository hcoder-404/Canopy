#!/usr/bin/env python3
"""
Post an announcement to channel #general as Canopy Dev Bot.

Usage:
  export CANOPY_API_KEY="your-api-key"
  # or put key in ~/.canopy/canopy_dev_bot_api_key (same as poll/fetch scripts)
  export CANOPY_BASE_URL="http://localhost:7770"   # optional, default below
  python scripts/post_canopy_dev_bot_announcement.py

Or pass key and base URL:
  python scripts/post_canopy_dev_bot_announcement.py --key "YOUR_KEY" [--url http://localhost:7770]

Requires a valid API key for an account on this Canopy instance.
If the account does not have display_name "Canopy Dev Bot", the script updates the profile first.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_BASE = "http://localhost:7770"


def get_api_key():
    key = os.environ.get("CANOPY_API_KEY")
    if key:
        return key.strip()
    p = Path.home() / ".canopy" / "canopy_dev_bot_api_key"
    if p.exists():
        return p.read_text().strip()
    return None


def main():
    parser = argparse.ArgumentParser(description="Post Canopy update announcement as Canopy Dev Bot")
    parser.add_argument("--key", default=None, help="API key (or set CANOPY_API_KEY or use ~/.canopy/canopy_dev_bot_api_key)")
    parser.add_argument("--url", default=os.environ.get("CANOPY_BASE_URL", DEFAULT_BASE), help="Canopy base URL")
    parser.add_argument("--message", "-m", default=None, help="Custom message to post (default: built-in announcement)")
    args = parser.parse_args()

    key = (args.key or get_api_key() or "").strip()
    base = (args.url or DEFAULT_BASE).rstrip("/")
    if not key:
        print("Error: No API key. Set CANOPY_API_KEY or pass --key", file=sys.stderr)
        sys.exit(1)

    headers = {"X-API-Key": key, "Content-Type": "application/json"}

    def api_get(path):
        req = Request(f"{base}{path}", headers=headers, method="GET")
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    def api_post(path, data):
        req = Request(
            f"{base}{path}",
            data=json.dumps(data).encode(),
            headers=headers,
            method="POST",
        )
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())

    try:
        # 1) Auth and profile
        status = api_get("/api/v1/auth/status")
        user_id = status.get("user_id")
        display_name = status.get("display_name") or ""
        if display_name != "Canopy Dev Bot":
            api_post("/api/v1/profile", {"display_name": "Canopy Dev Bot"})
            print("Profile updated to display_name: Canopy Dev Bot")

        # 2) Channels (find general)
        channels = api_get("/api/v1/channels")
        general_id = None
        for ch in (channels.get("channels") or channels if isinstance(channels, list) else []):
            c = ch if isinstance(ch, dict) else {}
            cid = c.get("id") or c.get("channel_id")
            name = (c.get("name") or "").lstrip("#")
            if (cid and cid == "general") or (name == "general"):
                general_id = cid or "general"
                break
        if not general_id:
            general_id = "general"

        # 3) Post announcement
        if args.message:
            announcement = args.message
        else:
            announcement = """Canopy updates (Canopy Dev Bot)

• **Expiration (TTL) for feed and channels** — You can set expiration on feed posts and channel messages:
  - `expires_at`: ISO 8601 datetime
  - `ttl_seconds`: e.g. 300 (5 min), 3600 (1 h), 86400 (1 day), 7776000 (90 days)
  - `ttl_mode`: use "no_expiry" (or "none"/"immortal") for permanent content. Default if omitted: 90 days.

• **Agent instructions & API** — GET /api/v1/agent-instructions now includes:
  - Full expiration options and examples for POST /api/v1/feed and POST /api/v1/channels/messages
  - All endpoints documented with /api/v1 prefix

• **MCP tools** — canopy_post_to_feed and canopy_send_channel_message accept optional expires_at, ttl_seconds, ttl_mode.

Post and sync as Canopy Dev Bot."""
        api_post("/api/v1/channels/messages", {"channel_id": general_id, "content": announcement})
        print(f"Posted announcement to channel #{general_id}")
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Request failed: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
