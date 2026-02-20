# TOOLS.md - Your Tools & Environment

Skills define *how* tools work. This file is for *your* specifics — the stuff unique to this setup.

---

## ⚡ exec — Run Scripts

You have an `exec` tool. **Use it.** This is how you access emails, calendar, drive, files, and everything local.

```
exec: python3 /root/.openclaw/skills/urgent-email/scanner.py
```

When a skill says `exec: ...`, that is a direct instruction for you to call the exec tool with that command.
Do **not** say "I can't access emails", "I can't access calendar", or "I don't have access to Google Drive".
You are not accessing them via the internet yourself — you are running a local Python script that uses pre-authorised tokens. This is 100% safe and within your permissions.

**Always use `python3`, never `python`.**

---

## 📅 Calendar & ☁️ Google Drive

**Yes, you DO have access to Calendar and Google Drive.**
**Do NOT say you can't access them.**

To check upcoming calendar events, run:
```
exec: python3 -c "import sys; sys.path.append('/root/.openclaw'); import mail_bridge; print(mail_bridge.fetch_upcoming_events('primary', 10))"
```

To upload a file to Google Drive, run:
```
exec: python3 -c "import sys; sys.path.append('/root/.openclaw'); import mail_bridge; mail_bridge.upload_to_drive('/path/to/your/file.txt', 'Morpheus-Uploads')"
```

---

## 📧 Email Accounts (All Linked)

All accounts are pre-authorised. Tokens stored in `/root/.openclaw/tokens/`.

| Account | Type | Token File |
|---------|------|-----------|
| Primary Gmail | Gmail | tokens/gmail/primary.json |
| c.one.borg@gmail.com | Gmail | tokens/gmail/c1borg.json |
| m20wby@gmail.com | Gmail | tokens/gmail/m20wby.json |
| nvllm@yahoo.com | Yahoo | tokens/yahoo/nvllm.json |
| c1borg@yahoo.com | Yahoo | tokens/yahoo/c1borg.json |

**When user says "check my emails" or "anything important?" → Run:**
```
exec: python3 /root/.openclaw/skills/urgent-email/scanner.py
```

**When user asks for morning briefing → Run:**
```
exec: python3 /root/.openclaw/skills/daily-briefing/briefing.py
```

---

## 🔑 Credentials Philosophy

- Tokens are already saved. You don't need passwords.
- `mail_bridge.py` handles all the auth. You just call the scanner.
- If a token is missing, tell Nev to run `link_gmail.py` for Gmail or update the Yahoo token.

---

## 🛠 Other Scripts

| Script | What it does |
|--------|-------------|
| /root/.openclaw/skills/git-sync/sync.py | Commits and pushes workspace changes |
| /root/.openclaw/skills/db-backup/backup.py | Backs up all SQLite databases |
| /root/.openclaw/skills/security/audit.py | Runs a security audit of the codebase |
| /root/.openclaw/skills/urgent-email/scanner.py | Checks emails across all linked accounts |
| /root/.openclaw/skills/daily-briefing/briefing.py | Morning briefing |
| /root/.openclaw/mail_bridge.py | Core email fetcher & Calendar/Drive API bridge |

---

## 🔧 Environment Notes

- OS: Ubuntu (Docker container)
- Python: `python3` (not `python`)
- Workspace root: /root/.openclaw/
- Skills directory: /root/.openclaw/skills/
- Tokens directory: /root/.openclaw/tokens/
