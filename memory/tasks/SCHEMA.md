# Task History Schema

Each task entry follows this format. Append-only — never edit after writing.

```
## [YYYY-MM-DD HH:MM] Task: [short description]

**Status:** done | failed | pending
**Source:** telegram | cron | heartbeat | manual
**Summary:** One sentence of what happened.
**Notes:** Any relevant detail, errors, or follow-up needed.
```

---

## 2026-02-18 16:00 Task: Gmail OAuth setup

**Status:** done
**Source:** manual
**Summary:** Connected Google account, saved token to tokens/gmail/primary.json.
**Notes:** Scopes include gmail.modify, calendar.readonly, drive.readonly.
