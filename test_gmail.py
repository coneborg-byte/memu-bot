import sys
sys.stdout.reconfigure(encoding='utf-8')
from gmail_bridge import fetch_recent_emails, fetch_upcoming_events

print('=== Last 3 Emails ===')
emails = fetch_recent_emails('primary', 3)
for e in emails:
    print(f"From: {e['from'][:60]}")
    print(f"Subject: {e['subject'][:70]}")
    print()

print('=== Next 3 Calendar Events ===')
events = fetch_upcoming_events('primary', 3)
for ev in events:
    print(f"{ev['start']} - {ev['summary']}")
