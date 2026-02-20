#!/usr/bin/env python3
"""
Gmail Account Linker - Morpheus AI
Run this locally to authorize a new Gmail account.

Usage:
  python3 link_gmail.py <account_name>

Examples:
  python3 link_gmail.py c1borg    # links c.one.borg@gmail.com -> tokens/gmail/c1borg.json
  python3 link_gmail.py m20wby    # links m20wby@gmail.com     -> tokens/gmail/m20wby.json
"""

import sys
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from mail_bridge import get_google_service

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 link_gmail.py <account_name>")
        print("  e.g. python3 link_gmail.py c1borg")
        sys.exit(1)

    account_id = sys.argv[1]
    print(f"Linking Gmail account: {account_id}")
    print("A browser window will open for Google OAuth authorization...")
    print("Sign in with the correct Google account when prompted.\n")

    service = get_google_service('gmail', 'v1', account_id)
    if service:
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress', 'unknown')
        print(f"\n✅ Successfully linked: {email}")
        print(f"   Token saved to: tokens/gmail/{account_id}.json")
    else:
        print("\n❌ Linking failed. Check credentials.json exists and try again.")
