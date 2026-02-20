#!/usr/bin/env python3
"""Test: upload image, post to #general with attachment, then delete the message."""
import base64
import json
import os
import sys
from pathlib import Path

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    Request, urlopen, HTTPError, URLError = None, None, None, None

REPO = Path(__file__).resolve().parent.parent
BASE = os.environ.get("CANOPY_BASE_URL", "http://localhost:7770").rstrip("/")


def get_api_key():
    key = os.environ.get("CANOPY_API_KEY")
    if key:
        return key.strip()
    p = Path.home() / ".canopy" / "canopy_dev_bot_api_key"
    if p.exists():
        return p.read_text().strip()
    return None


def main():
    key = get_api_key()
    if not key:
        print("No CANOPY_API_KEY or ~/.canopy/canopy_dev_bot_api_key", file=sys.stderr)
        sys.exit(1)

    headers = {"X-API-Key": key, "Content-Type": "application/json"}

    # 1) Upload image (canopy logo)
    img_path = REPO / "canopy" / "ui" / "static" / "icons" / "canopy-logo.png"
    if not img_path.exists():
        print(f"Image not found: {img_path}", file=sys.stderr)
        sys.exit(1)
    data_b64 = base64.b64encode(img_path.read_bytes()).decode()
    upload_body = {
        "filename": "canopy-logo.png",
        "content_type": "image/png",
        "data": data_b64,
    }
    req = Request(
        f"{BASE}/api/v1/files/upload",
        data=json.dumps(upload_body).encode(),
        headers=headers,
        method="POST",
    )
    with urlopen(req, timeout=15) as r:
        upload_res = json.loads(r.read().decode())
    file_id = upload_res.get("file_id")
    if not file_id:
        print("Upload failed:", upload_res, file=sys.stderr)
        sys.exit(1)
    print("Uploaded file_id:", file_id)

    # 2) Post to #general with attachment
    post_body = {
        "channel_id": "general",
        "content": "Test message with embedded image (will be deleted).",
        "attachments": [
            {"id": file_id, "name": "canopy-logo.png", "type": "image/png"}
        ],
        "ttl_mode": "no_expiry",
    }
    req = Request(
        f"{BASE}/api/v1/channels/messages",
        data=json.dumps(post_body).encode(),
        headers=headers,
        method="POST",
    )
    with urlopen(req, timeout=15) as r:
        post_res = json.loads(r.read().decode())
    msg_id = post_res.get("message", {}).get("id")
    if not msg_id:
        print("Post failed:", post_res, file=sys.stderr)
        sys.exit(1)
    print("Posted message_id:", msg_id)

    # 3) Delete the message
    req = Request(
        f"{BASE}/api/v1/channels/general/messages/{msg_id}",
        headers=headers,
        method="DELETE",
    )
    with urlopen(req, timeout=15) as r:
        del_res = json.loads(r.read().decode())
    if del_res.get("success"):
        print("Deleted message successfully.")
    else:
        print("Delete failed:", del_res, file=sys.stderr)
        sys.exit(1)
    print("Done: create + delete with embedded image OK.")


if __name__ == "__main__":
    main()
