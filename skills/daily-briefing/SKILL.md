---
name: daily-briefing
description: >
  Daily morning briefing. Use when: user asks for their daily briefing, morning summary, 
  what's on today, or when the 7am cron fires. Pulls today's calendar events and recent 
  emails, then delivers a single consolidated morning message to Nev.
---

# Daily Briefing Skill

## What This Does

Generates a single consolidated morning briefing covering:
1. Today's calendar events (with context)
2. Urgent/unread emails from the last 24 hours
3. Pending items from the missions/ folder
4. A one-line weather note (if relevant)

## How to Use It

Run the briefing:
```
exec: python /root/.openclaw/workspace/skills/daily-briefing/briefing.py
```

## Output Format

Deliver as a single Telegram message. Structure:

```
🌅 Morning Briefing — [Day, Date]

📅 TODAY
• [time] — [event title]
• [time] — [event title]

📧 EMAILS (last 24h)
• [sender]: [subject]
• [sender]: [subject]

📋 PENDING
• [any missions/ items waiting]

---
[One sharp closing line. Optional weather if relevant.]
```

## Rules

- One message only. No back-and-forth.
- Keep it tight — this is a briefing, not an essay.
- If calendar is empty, say so in one line. Don't pad it.
- If no urgent emails, skip that section entirely.
- Deliver at 07:00 GMT via the cron job. Don't wait to be asked.
