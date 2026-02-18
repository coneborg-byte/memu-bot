---
name: git-sync
description: >
  Git auto-sync. Use when: user asks to sync, push, or commit changes, or when the hourly
  cron fires. Commits all workspace changes and pushes to the remote repository. Detects
  merge conflicts and notifies Nev instead of forcing a resolution. Tags each sync with
  a timestamp. Never commits sensitive data like .env files or session tokens.
---

# Git Sync Skill

## What This Does

- Stages all workspace changes
- Commits with a timestamp tag
- Pushes to the remote repository
- Detects merge conflicts — notifies Nev, never force-resolves
- Pre-commit check blocks sensitive files (.env, tokens/, cookies)

## How to Use It

Run a sync:
```
exec: python /root/.openclaw/workspace/skills/git-sync/sync.py
```

Check status only (no commit):
```
exec: python /root/.openclaw/workspace/skills/git-sync/sync.py --status
```

## Conflict Handling

If a merge conflict is detected:
- Do NOT force push or rebase automatically
- Tell Nev: "Merge conflict on [branch] — needs manual resolution before next sync."
- Skip the push, leave the local commit intact

## Sensitive Data Rules

Never commit:
- `.env` files
- `tokens/` directory
- `*.sqlite` or `*.db` files
- Browser profile cookies or session tokens
- Any file matching `*secret*`, `*credential*`, `*password*`

If a blocked file is staged, remove it and warn Nev.

## Schedule

Runs hourly via cron. Each commit is tagged: `auto-sync-YYYY-MM-DDTHH-MM`
