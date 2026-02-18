#!/usr/bin/env python3
"""
Urgent Email Detection - Morpheus AI
Based on OpenClaw prompt #3 from the video.

Scans Gmail every 30 minutes during waking hours (08:00-23:00 GMT).
Uses local Ollama to classify urgency.
Delivers alerts to Telegram via the bot token.
Learns from feedback over time via urgent_senders.json / noise_senders.json.
"""

import sys
import json
import os
import datetime
import requests
import time

sys.stdout.reconfigure(encoding='utf-8')

# --- Config ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"
STATE_FILE = "memory/email_scan_state.json"
NOISE_FILE = "memory/noise_senders.json"
URGENT_FILE = "memory/urgent_senders.json"

WAKING_HOURS_START = 8   # 08:00 GMT
WAKING_HOURS_END = 23    # 23:00 GMT

# --- Known noise senders (pre-seeded, user can add more) ---
DEFAULT_NOISE_DOMAINS = [
    "noreply@", "no-reply@", "donotreply@", "newsletter@",
    "marketing@", "promotions@", "notifications@", "updates@",
    "info@highspeedcomps.com", "donotreply@ebuyer.com",
]

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def is_waking_hours():
    now = datetime.datetime.utcnow()
    return WAKING_HOURS_START <= now.hour < WAKING_HOURS_END

def is_noise_sender(sender: str, noise_list: list) -> bool:
    sender_lower = sender.lower()
    for noise in noise_list + DEFAULT_NOISE_DOMAINS:
        if noise.lower() in sender_lower:
            return True
    return False

def classify_urgency(subject: str, snippet: str, sender: str) -> bool:
    """Ask local Ollama if this email is urgent."""
    prompt = f"""You are an email urgency classifier. Respond with only 'URGENT' or 'NOT_URGENT'.

An email is URGENT if it requires action within 24 hours, involves money, legal matters,
health, security alerts, or is from a real person (not a company) asking something important.

Email:
From: {sender}
Subject: {subject}
Preview: {snippet}

Classification:"""

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 1024, "temperature": 0}
        }, timeout=30)
        result = resp.json().get("response", "").strip().upper()
        return "URGENT" in result
    except Exception as e:
        print(f"Ollama error: {e}")
        return False

def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[TELEGRAM] {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }, timeout=10)

def scan_emails():
    from gmail_bridge import fetch_recent_emails

    state = load_json(STATE_FILE, {"seen_ids": [], "last_scan": None})
    noise_senders = load_json(NOISE_FILE, [])
    urgent_senders = load_json(URGENT_FILE, [])

    if not is_waking_hours():
        print("Outside waking hours, skipping scan.")
        return

    print(f"Scanning emails at {datetime.datetime.utcnow().isoformat()}...")
    emails = fetch_recent_emails('primary', max_results=10)

    new_urgent = []
    for email in emails:
        msg_id = email['id']
        if msg_id in state["seen_ids"]:
            continue

        state["seen_ids"].append(msg_id)
        # Keep seen_ids from growing unbounded
        state["seen_ids"] = state["seen_ids"][-500:]

        sender = email.get('from', '')
        subject = email.get('subject', '')
        snippet = email.get('snippet', '')

        # Pre-filter known noise
        if is_noise_sender(sender, noise_senders):
            print(f"  [NOISE] {sender}: {subject}")
            continue

        # Known urgent sender — always alert
        if any(u.lower() in sender.lower() for u in urgent_senders):
            new_urgent.append(email)
            continue

        # Ask Ollama
        is_urgent = classify_urgency(subject, snippet, sender)
        print(f"  [{'URGENT' if is_urgent else 'ok'}] {sender}: {subject}")
        if is_urgent:
            new_urgent.append(email)

    state["last_scan"] = datetime.datetime.utcnow().isoformat()
    save_json(STATE_FILE, state)

    if new_urgent:
        lines = ["🚨 *Urgent Email Alert*\n"]
        for e in new_urgent:
            lines.append(f"📧 *From:* {e['from'][:50]}")
            lines.append(f"📌 *Subject:* {e['subject'][:70]}")
            lines.append(f"💬 _{e['snippet'][:100]}_\n")
        send_telegram("\n".join(lines))
        print(f"Sent {len(new_urgent)} urgent alert(s).")
    else:
        print("No urgent emails found.")

if __name__ == "__main__":
    # Load env
    from dotenv import load_dotenv
    load_dotenv()
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    # Get chat ID from args or env
    if len(sys.argv) > 1:
        TELEGRAM_CHAT_ID = sys.argv[1]
    else:
        TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

    scan_emails()
