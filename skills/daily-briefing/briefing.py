#!/usr/bin/env python3
"""
Daily Morning Briefing - Morpheus AI
Skill: daily-briefing

Generates a consolidated morning briefing covering:
- Today's calendar events (Gmail)
- Recent emails from ALL linked accounts (Gmail & Yahoo)
- Pending missions

Designed to be called by OpenClaw cron at 07:00 GMT daily.
"""

import sys
import os
import datetime
import json
import glob

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MISSIONS_DIR = os.path.join(WORKSPACE, "missions")
NOISE_FILE  = os.path.join(WORKSPACE, "memory", "noise_senders.json")

DEFAULT_NOISE = [
    "noreply@", "no-reply@", "donotreply@", "newsletter@",
    "marketing@", "notifications@", "updates@", "mailer@",
    "info@highspeedcomps", "donotreply@ebuyer",
    "msemoneytips@", "24hours@mail.firstdirect",
]


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def is_noise(sender: str, noise_list: list) -> bool:
    s = sender.lower()
    return any(p.lower() in s for p in DEFAULT_NOISE + noise_list)


def get_calendar_events():
    sys.path.insert(0, WORKSPACE)
    from mail_bridge import fetch_upcoming_events
    try:
        # Currently only checks 'primary' Gmail account for calendar
        events = fetch_upcoming_events("primary", max_results=10)
        today = datetime.datetime.now(datetime.timezone.utc).date()
        today_events = []
        for ev in events:
            start = ev.get("start", "")
            try:
                if "T" in start:
                    dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                    if dt.date() == today:
                        time_str = dt.strftime("%H:%M")
                        today_events.append(f"• {time_str} — {ev['summary']}")
                else:
                    ev_date = datetime.date.fromisoformat(start)
                    if ev_date == today:
                        today_events.append(f"• All day — {ev['summary']}")
            except Exception:
                today_events.append(f"• {ev['summary']}")
        return today_events
    except Exception as e:
        return [f"• (calendar error: {e})"]


def get_recent_emails():
    sys.path.insert(0, WORKSPACE)
    from mail_bridge import fetch_all_recent_emails
    noise_list = load_json(NOISE_FILE, [])
    try:
        # Fetch up to 10 recent emails from all accounts
        emails = fetch_all_recent_emails(max_results_per_account=5)
        
        # Sort by type and account for cleaner briefing
        emails.sort(key=lambda x: (x['type'], x['account']))
        
        items = []
        for e in emails:
            sender  = e.get("from", "")
            subject = e.get("subject", "")
            acc_id  = e.get("account", "")
            acc_type = e.get("type", "")
            
            if is_noise(sender, noise_list):
                continue
                
            sender_short = sender.split("<")[0].strip().strip('"') or sender
            items.append(f"• [{acc_type}] {sender_short[:30]}: {subject[:50]}")
            
            if len(items) >= 10: # Cap briefing size
                break
        return items
    except Exception as e:
        return [f"• (email error: {e})"]


def get_pending_missions():
    if not os.path.exists(MISSIONS_DIR):
        return []
    files = glob.glob(os.path.join(MISSIONS_DIR, "*.json"))
    items = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("status") in ["pending", "notified_cloud"]:
                task = data.get("task") or data.get("action") or os.path.basename(f)
                items.append(f"• {task[:70]}")
        except Exception:
            pass
    return items


def build_briefing():
    now = datetime.datetime.now(datetime.timezone.utc)
    day_str = now.strftime("%A, %d %B %Y")

    lines = [f"🌅 Morning Briefing — {day_str}\n"]

    # Calendar
    events = get_calendar_events()
    lines.append("📅 TODAY")
    if events:
        lines.extend(events)
    else:
        lines.append("• Nothing scheduled — clear day.")
    lines.append("")

    # Emails
    emails = get_recent_emails()
    if emails:
        lines.append("📧 RECENT EMAILS")
        lines.extend(emails)
        lines.append("")

    # Pending missions
    missions = get_pending_missions()
    if missions:
        lines.append("📋 PENDING MISSIONS")
        lines.extend(missions)
        lines.append("")

    lines.append("---")
    lines.append("Have a good one, Nev. 🦾")

    return "\n".join(lines)


if __name__ == "__main__":
    print(build_briefing())
