#!/usr/bin/env python3
"""
Urgent Email Scanner - Morpheus AI
Skill: urgent-email

Scans ALL linked Gmail and Yahoo accounts for urgent emails during waking hours.
Uses local Ollama (llama3.1:8b) to classify urgency.
Learns from feedback via noise_senders.json and urgent_senders.json.

Usage:
  python scanner.py                          # Run a scan
  python scanner.py --mark-noise "x@y.com"   # Add to noise list
  python scanner.py --mark-urgent "x@y.com"  # Add to always-urgent list
"""

import sys
import json
import os
import datetime
import requests
import argparse

sys.stdout.reconfigure(encoding='utf-8')

# Paths (relative to workspace root, which is the working dir when called via exec)
WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE  = os.path.join(WORKSPACE, "memory", "email_scan_state.json")
NOISE_FILE  = os.path.join(WORKSPACE, "memory", "noise_senders.json")
URGENT_FILE = os.path.join(WORKSPACE, "memory", "urgent_senders.json")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434/api/generate")
MODEL      = "llama3.1:8b"

WAKING_START = 8   # 08:00 GMT
WAKING_END   = 23  # 23:00 GMT

# Pre-seeded noise patterns — never classify these
DEFAULT_NOISE = [
    "noreply@", "no-reply@", "donotreply@", "do-not-reply@",
    "newsletter@", "marketing@", "notifications@", "updates@",
    "mailer@", "bounce@", "support@", "info@highspeedcomps",
    "donotreply@ebuyer", "no-reply@accounts.google.com",
]


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


def is_waking_hours():
    now = datetime.datetime.utcnow()
    return WAKING_START <= now.hour < WAKING_END


def is_noise(sender: str, noise_list: list) -> bool:
    s = sender.lower()
    for pattern in DEFAULT_NOISE + noise_list:
        if pattern.lower() in s:
            return True
    return False


def is_always_urgent(sender: str, urgent_list: list) -> bool:
    s = sender.lower()
    return any(u.lower() in s for u in urgent_list)


def classify(subject: str, snippet: str, sender: str) -> bool:
    """Ask local Ollama if this email is urgent. Returns True if urgent."""
    prompt = (
        "You are an email urgency classifier. Reply with only 'URGENT' or 'NOT_URGENT'.\n\n"
        "An email is URGENT if it requires action within 24 hours, involves money, legal matters, "
        "health, account security, or is from a real person (not a company) asking something important.\n\n"
        f"From: {sender}\nSubject: {subject}\nPreview: {snippet}\n\nClassification:"
    )
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 512, "temperature": 0}
        }, timeout=30)
        result = resp.json().get("response", "").strip().upper()
        return "URGENT" in result
    except Exception as e:
        print(f"[classifier error] {e}", file=sys.stderr)
        return False


def scan():
    if not is_waking_hours():
        print("HEARTBEAT_OK (outside waking hours)")
        return

    # Import mail_bridge from workspace root
    sys.path.insert(0, WORKSPACE)
    from mail_bridge import fetch_all_recent_emails

    state        = load_json(STATE_FILE, {"seen_ids": []})
    noise_list   = load_json(NOISE_FILE, [])
    urgent_list  = load_json(URGENT_FILE, [])

    print(f"Scanning all accounts at {datetime.datetime.utcnow().strftime('%H:%M UTC')}...")
    emails = fetch_all_recent_emails(max_results_per_account=10)

    urgent_found = []

    for email in emails:
        msg_id  = email["id"]
        sender  = email.get("from", "")
        subject = email.get("subject", "")
        snippet = email.get("snippet", "")
        acc_id  = email.get("account", "unknown")
        acc_type = email.get("type", "unknown")

        # Global unique ID check
        unique_id = f"{acc_type}_{acc_id}_{msg_id}"

        if unique_id in state["seen_ids"]:
            continue

        # Mark as seen
        state["seen_ids"].append(unique_id)
        state["seen_ids"] = state["seen_ids"][-1000:]  # cap size

        if is_noise(sender, noise_list):
            print(f"  [noise]  {sender[:50]}")
            continue

        if is_always_urgent(sender, urgent_list):
            print(f"  [always-urgent] {sender[:50]}: {subject[:60]}")
            urgent_found.append(email)
            continue

        is_urg = classify(subject, snippet, sender)
        label  = "URGENT" if is_urg else "ok"
        print(f"  [{label}] ({acc_type}:{acc_id}) {sender[:40]}: {subject[:50]}")
        if is_urg:
            urgent_found.append(email)

    save_json(STATE_FILE, state)

    if urgent_found:
        print("\n--- URGENT EMAILS ---")
        for e in urgent_found:
            print(f"Account: [{e['type']}:{e['account']}]")
            print(f"From:    {e['from']}")
            print(f"Subject: {e['subject']}")
            print(f"Preview: {e['snippet'][:120]}")
            print()
    else:
        print("HEARTBEAT_OK (no urgent emails)")


def mark_noise(sender: str):
    data = load_json(NOISE_FILE, [])
    if sender not in data:
        data.append(sender)
        save_json(NOISE_FILE, data)
        print(f"Added to noise list: {sender}")
    else:
        print(f"Already in noise list: {sender}")


def mark_urgent(sender: str):
    data = load_json(URGENT_FILE, [])
    if sender not in data:
        data.append(sender)
        save_json(URGENT_FILE, data)
        print(f"Added to always-urgent list: {sender}")
    else:
        print(f"Already in always-urgent list: {sender}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mark-noise",  metavar="SENDER", help="Add sender to noise list")
    parser.add_argument("--mark-urgent", metavar="SENDER", help="Add sender to always-urgent list")
    args = parser.parse_args()

    if args.mark_noise:
        mark_noise(args.mark_noise)
    elif args.mark_urgent:
        mark_urgent(args.mark_urgent)
    else:
        scan()
