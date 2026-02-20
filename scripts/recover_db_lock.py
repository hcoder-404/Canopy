#!/usr/bin/env python3
"""
Recover from SQLite lock storm: stop Canopy, clear stale WAL/shm, then you can restart.

Run from repo root:
  ./venv/bin/python scripts/recover_db_lock.py

Or with explicit DB path:
  ./venv/bin/python scripts/recover_db_lock.py --db path/to/canopy.db
"""
import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Recover Canopy DB from lock storm")
    parser.add_argument(
        "--db",
        help="Path to canopy.db (default: auto-detect under data/devices/)",
    )
    parser.add_argument(
        "--no-kill",
        action="store_true",
        help="Do not kill Canopy processes (e.g. you already stopped them)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be done",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    if not args.no_kill:
        print("Stopping any Canopy processes...")
        if not args.dry_run:
            subprocess.run(
                ["pkill", "-f", "canopy.main"],
                capture_output=True,
            )
            import time
            time.sleep(2)
        else:
            print("  [dry-run] would run: pkill -f canopy.main ; sleep 2")

    db_paths = []
    if args.db:
        p = Path(args.db).resolve()
        if not p.exists():
            print(f"DB path does not exist: {p}", file=sys.stderr)
            sys.exit(1)
        db_paths.append(p)
    else:
        devices_dir = repo_root / "data" / "devices"
        if not devices_dir.exists():
            print("No data/devices directory found.", file=sys.stderr)
            sys.exit(1)
        for device_dir in devices_dir.iterdir():
            if device_dir.is_dir():
                db_file = device_dir / "canopy.db"
                if db_file.exists():
                    db_paths.append(db_file)

    if not db_paths:
        print("No canopy.db found.", file=sys.stderr)
        sys.exit(1)

    for db_path in db_paths:
        print(f"\nDatabase: {db_path}")
        wal = Path(str(db_path) + "-wal")
        shm = Path(str(db_path) + "-shm")
        for name, path in [("WAL", wal), ("SHM", shm)]:
            if path.exists():
                bak = path.with_suffix(path.suffix + ".bak")
                if args.dry_run:
                    print(f"  [dry-run] would rename {path} -> {bak}")
                else:
                    path.rename(bak)
                    print(f"  Renamed {name} file to {bak.name}")
            else:
                print(f"  No {name} file (OK)")

    print("\nDone. Start Canopy again with:")
    print("  ./venv/bin/python -m canopy.main --host 0.0.0.0 --port 7770")
    return 0


if __name__ == "__main__":
    sys.exit(main())
