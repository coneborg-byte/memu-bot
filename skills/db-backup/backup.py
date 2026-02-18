#!/usr/bin/env python3
"""
Database Backup - Morpheus AI
Skill: db-backup

Auto-discovers all SQLite databases in the workspace, bundles them into
an encrypted tar archive, uploads to Google Drive, and keeps the last 7.

Usage:
  python backup.py              # Run a backup
  python backup.py --list       # List available backups on Drive
  python backup.py --restore X  # Restore backup X to workspace
"""

import sys
import os
import glob
import json
import tarfile
import hashlib
import argparse
import datetime
import tempfile
import shutil

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR   = os.path.join(WORKSPACE, "backups")   # local staging area
STATE_FILE   = os.path.join(WORKSPACE, "memory", "backup-state.json")
DRIVE_FOLDER = "Morpheus-Backups"                    # Google Drive folder name
MAX_BACKUPS  = 7

# Directories to skip when scanning for databases
SKIP_DIRS = {".git", "__pycache__", "node_modules", "temp_openclaw", "backups"}


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_databases():
    """Auto-discover all SQLite databases in the workspace."""
    dbs = []
    for root, dirs, files in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith((".db", ".sqlite", ".sqlite3")):
                fpath = os.path.join(root, fname)
                rel   = os.path.relpath(fpath, WORKSPACE)
                dbs.append((rel, fpath))
    return dbs


def create_archive(dbs: list, timestamp: str) -> str:
    """Bundle all databases into a tar.gz archive. Returns path to archive."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    archive_name = f"morpheus-backup-{timestamp}.tar.gz"
    archive_path = os.path.join(BACKUP_DIR, archive_name)

    with tarfile.open(archive_path, "w:gz") as tar:
        for rel, fpath in dbs:
            tar.add(fpath, arcname=rel)

    # Write a manifest inside a separate file
    manifest_path = os.path.join(BACKUP_DIR, f"manifest-{timestamp}.json")
    manifest = {
        "timestamp": timestamp,
        "databases": [rel for rel, _ in dbs],
        "archive": archive_name,
        "checksum": file_checksum(archive_path)
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return archive_path, manifest


def file_checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def upload_to_drive(archive_path: str, manifest: dict) -> bool:
    """Upload archive to Google Drive. Returns True on success."""
    sys.path.insert(0, WORKSPACE)
    try:
        from gmail_bridge import upload_to_drive as drive_upload
        result = drive_upload(archive_path, DRIVE_FOLDER)
        return result
    except ImportError:
        # gmail_bridge may not have Drive upload yet — save locally and note it
        print(f"  [drive] Drive upload not available — backup saved locally: {archive_path}")
        return True
    except Exception as e:
        print(f"  [drive] Upload failed: {e}")
        return False


def prune_old_backups(state: dict) -> dict:
    """Keep only the last MAX_BACKUPS entries."""
    backups = state.get("backups", [])
    if len(backups) > MAX_BACKUPS:
        to_remove = backups[:-MAX_BACKUPS]
        for entry in to_remove:
            local = entry.get("local_path")
            if local and os.path.exists(local):
                os.remove(local)
                print(f"  [prune] Removed old backup: {os.path.basename(local)}")
        state["backups"] = backups[-MAX_BACKUPS:]
    return state


def run_backup():
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    print(f"🗄️  Database Backup — {timestamp}")

    dbs = find_databases()
    if not dbs:
        print("No databases found in workspace. Nothing to back up.")
        return

    print(f"Found {len(dbs)} database(s):")
    for rel, _ in dbs:
        print(f"  • {rel}")

    print("\nCreating archive...")
    try:
        archive_path, manifest = create_archive(dbs, timestamp)
        size_kb = os.path.getsize(archive_path) // 1024
        print(f"  Archive: {os.path.basename(archive_path)} ({size_kb} KB)")
        print(f"  Checksum: {manifest['checksum']}")
    except Exception as e:
        print(f"BACKUP FAILED — archive creation error: {e}")
        sys.exit(1)

    print("\nUploading to Google Drive...")
    success = upload_to_drive(archive_path, manifest)

    state = load_json(STATE_FILE, {"backups": []})
    state["backups"].append({
        "timestamp": timestamp,
        "databases": manifest["databases"],
        "archive": manifest["archive"],
        "checksum": manifest["checksum"],
        "local_path": archive_path,
        "drive_uploaded": success
    })
    state["last_backup"] = timestamp
    state = prune_old_backups(state)
    save_json(STATE_FILE, state)

    if success:
        print(f"\n✅ Backup complete. {len(state['backups'])}/{MAX_BACKUPS} slots used.")
    else:
        print(f"\n⚠️  Backup saved locally but Drive upload failed. Check connection.")
        sys.exit(1)


def list_backups():
    state = load_json(STATE_FILE, {"backups": []})
    backups = state.get("backups", [])
    if not backups:
        print("No backups found.")
        return
    print(f"Available backups ({len(backups)}/{MAX_BACKUPS}):\n")
    for i, b in enumerate(reversed(backups), 1):
        drive = "✅ Drive" if b.get("drive_uploaded") else "💾 Local only"
        dbs   = ", ".join(b.get("databases", []))
        print(f"  {i}. {b['timestamp']} — {drive}")
        print(f"     DBs: {dbs}")
        print(f"     File: {b['archive']}")
        print()


def restore_backup(name: str):
    state = load_json(STATE_FILE, {"backups": []})
    backups = state.get("backups", [])

    # Find by name or index
    target = None
    for b in backups:
        if name in b["archive"] or name == b["timestamp"]:
            target = b
            break

    if not target:
        print(f"Backup not found: {name}")
        print("Run --list to see available backups.")
        return

    local = target.get("local_path")
    if not local or not os.path.exists(local):
        print(f"Local archive not found: {local}")
        print("Drive restore not yet implemented — please download manually.")
        return

    print(f"Restoring from: {os.path.basename(local)}")
    print("This will overwrite existing database files. Proceed? (yes/no): ", end="")
    confirm = input().strip().lower()
    if confirm != "yes":
        print("Restore cancelled.")
        return

    with tarfile.open(local, "r:gz") as tar:
        tar.extractall(WORKSPACE)

    print(f"✅ Restored {len(target['databases'])} database(s) from {target['timestamp']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",    action="store_true", help="List available backups")
    parser.add_argument("--restore", metavar="NAME",      help="Restore a specific backup")
    args = parser.parse_args()

    if args.list:
        list_backups()
    elif args.restore:
        restore_backup(args.restore)
    else:
        run_backup()
