---
name: urgent-email
description: >
  Urgent email detection. Use when: user asks to check emails, asks if anything important came in,
  or when running a scheduled email scan. Scans Gmail for urgent messages, classifies them with AI,
  and reports back. Also handles feedback ("that wasn't urgent" / "that was urgent") to improve
  the noise/urgent sender lists over time.
---

# Urgent Email Skill

## What This Does

Scans Gmail for urgent emails, filters known noise senders, and reports anything that needs attention.
Learns from feedback over time.

## How to Use It

Run the scanner:
```
exec: python /root/.openclaw/workspace/skills/urgent-email/scanner.py
```

To mark a sender as noise (after user says "that wasn't urgent"):
```
exec: python /root/.openclaw/workspace/skills/urgent-email/scanner.py --mark-noise "sender@example.com"
```

To mark a sender as always urgent:
```
exec: python /root/.openclaw/workspace/skills/urgent-email/scanner.py --mark-urgent "sender@example.com"
```

## Output Format

If urgent emails found, report them clearly:
- Who it's from
- Subject line
- One-line snippet
- Ask Nev if he wants to read the full email or take action

If nothing urgent: reply `HEARTBEAT_OK` silently — don't announce it.

## Time Gates

Only scan during waking hours (08:00–23:00 GMT). Outside those hours, skip and reply `HEARTBEAT_OK`.

## Feedback Loop

When Nev says "that wasn't urgent" about an email you flagged, call `--mark-noise` with that sender.
When Nev says "always flag emails from X", call `--mark-urgent` with that sender.
The lists persist in `memory/noise_senders.json` and `memory/urgent_senders.json`.
