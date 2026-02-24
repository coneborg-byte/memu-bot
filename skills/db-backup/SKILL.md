---
name: db-backup
description: >
  Database backup system. Use when: user asks to back up databases, restore a backup,
  or when the hourly cron fires. Auto-discovers all SQLite databases in the workspace,
  bundles them into an encrypted archive, uploads to Google Drive, and keeps the last 7.
  Alerts Nev immediately on any failure.
---

# Database Backup Skill

## What This Does

- Auto-discovers all `.db` and `.sqlite` files in the workspace (no manual config needed)
- Bundles them into an encrypted `.tar.gz` archive
- Uploads to Google Drive backup folder
- Keeps the last 7 backups (auto-deletes older ones)
- Includes a full restore script

## How to Use It

Run a backup:
```
exec: python3 /root/.openclaw/skills/db-backup/backup.py
```

List available backups:
```
exec: python3 /root/.openclaw/skills/db-backup/backup.py --list
```

Restore a specific backup:
```
exec: python3 /root/.openclaw/skills/db-backup/backup.py --restore [backup-filename]
```

## Failure Handling

If any backup fails, report it to Nev immediately — don't wait for the next scheduled run.
Include: which database failed, the error, and what to do about it.

## Schedule

Runs hourly via cron. New databases are picked up automatically — no config needed.
