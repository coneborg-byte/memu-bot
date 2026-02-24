#!/usr/bin/env python3
"""
Security Audit - Morpheus AI
Skill: security

Analyses the codebase from four perspectives using local Ollama.
Produces a numbered findings report.
"""

import sys
import os
import json
import argparse
import requests
import datetime
import re

sys.stdout.reconfigure(encoding='utf-8')

ABSPATH = os.path.abspath(__file__)
WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(ABSPATH)))
OLLAMA_URL = os.environ.get(
    "OLLAMA_API_URL", "http://host.docker.internal:11434/api/generate"
)
MODEL = os.environ.get("MODEL_NAME", "llama3.1:8b")
FINDINGS_FILE = os.path.join(WORKSPACE, "memory", "security-findings.json")

# Telegram alerting (hardcoded for now, should ideally be in .env)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Fixed chat ID from logs for Nev
NEV_CHAT_ID = "8560438682"

PERSPECTIVES = {
    "offensive": (
        "You are a penetration tester. What could an attacker exploit in this "
        "code? Look for: hardcoded secrets, injection vulnerabilities, exposed "
        "endpoints, insecure dependencies, path traversal risks."
    ),
    "defensive": (
        "You are a defensive security engineer. Are protections adequate? Look "
        "for: input validation, error handling that leaks info, missing auth "
        "checks, insecure defaults, logging of sensitive data."
    ),
    "privacy": (
        "You are a data privacy auditor. Is sensitive data handled correctly? "
        "Look for: credentials in code, PII in logs, unencrypted storage of "
        "secrets, data sent to unexpected destinations."
    ),
    "operational": (
        "You are a pragmatic security reviewer. Are security measures "
        "practical or just theatre? Look for: security controls that are "
        "disabled, overly complex auth that gets bypassed, configs that "
        "contradict each other."
    ),
}

SCAN_EXTENSIONS = [".py", ".js", ".ts", ".json", ".env", ".md", ".sh", ".bat"]
SKIP_DIRS = {
    "temp_openclaw", ".git", "__pycache__", "node_modules", "docs", "init",
    ".pi"
}


def notify_telegram(message):
    """Send a notification to the user via Telegram."""
    if not TELEGRAM_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": NEV_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}", file=sys.stderr)


def collect_files():
    """Collect all relevant source files from the workspace."""
    files = []
    for root, dirs, filenames in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in SCAN_EXTENSIONS:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, WORKSPACE)
                files.append((rel, fpath))
    return files


def read_file_safe(path, max_chars=3000):
    """Read a file, truncating if too large."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        if len(content) == max_chars:
            content += "\n... [truncated]"
        return content
    except Exception as e:
        return f"[error reading file: {e}]"


def redact_secrets(text: str) -> str:
    """Redact obvious secrets from output before displaying."""
    pattern = (
        r'(token|key|secret|password|apikey)\s*[=:]\s*["\']?[\w\-\.]{10,}["\']?'
    )
    return re.sub(pattern, r'\1=***REDACTED***', text, flags=re.IGNORECASE)


def run_perspective(name: str, description: str, files: list) -> str:
    """Run one security perspective across all files."""
    print(f"\n[{name.upper()}] Analysing {len(files)} files...",
          file=sys.stderr)
    codebase_summary = []
    for rel, fpath in files[:20]:
        content = read_file_safe(fpath, max_chars=500)
        codebase_summary.append(f"=== {rel} ===\n{content}")

    codebase_text = "\n\n".join(codebase_summary)
    prompt = (
        f"{description}\n\n"
        f"Review this codebase and list your top findings as a numbered list.\n"
        f"For each finding: severity (CRITICAL/HIGH/MEDIUM/LOW), location, and "
        f"what the risk is.\n"
        f"Be specific. If nothing concerning, say 'No significant findings.'\n\n"
        f"CODEBASE:\n{codebase_text}\n\n"
        f"FINDINGS:"
    )

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 8192, "temperature": 0}
        }, timeout=120)
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"[error running {name} perspective: {e}]"


def full_audit():
    """Run a full security audit across all perspectives."""
    files = collect_files()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    date_str = now_utc.strftime('%Y-%m-%d %H:%M UTC')
    print(f"🔍 Security Audit — {date_str}")
    print(f"Scanning {len(files)} files across 4 perspectives...\n")

    all_findings = {}
    report_lines = [
        "🛡️ Security Audit Report",
        f"Date: {date_str}",
        f"Files scanned: {len(files)}",
        ""
    ]

    critical_count = 0
    for name, description in PERSPECTIVES.items():
        result = run_perspective(name, description, files)
        result = redact_secrets(result)
        report_lines.append(f"## {name.upper()}")
        report_lines.append(result)
        report_lines.append("")
        all_findings[name] = result
        if "CRITICAL" in result.upper():
            critical_count += result.upper().count("CRITICAL")

    os.makedirs(os.path.dirname(FINDINGS_FILE), exist_ok=True)
    with open(FINDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "date": now_utc.isoformat(),
            "findings": all_findings
        }, f, indent=2, ensure_ascii=False)

    print("\n".join(report_lines))

    if critical_count > 0:
        msg = f"❗ *Security Warning*: {critical_count} CRITICAL findings detected."
        msg += "\nRun `Morpheus harden` or check logs for details."
        notify_telegram(msg)


def single_perspective(name: str):
    """Run a single perspective analysis."""
    if name not in PERSPECTIVES:
        options = ', '.join(PERSPECTIVES.keys())
        print(f"Unknown perspective: {name}. Choose from: {options}")
        sys.exit(1)
    files = collect_files()
    result = run_perspective(name, PERSPECTIVES[name], files)
    result = redact_secrets(result)
    print(f"🛡️ {name.upper()} Perspective\n")
    print(result)


def show_finding():
    """Show the results of the last audit."""
    if not os.path.exists(FINDINGS_FILE):
        print("No findings file found. Run a full audit first.")
        return
    with open(FINDINGS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Last audit: {data.get('date', 'unknown')}\n")
    for name, content in data.get("findings", {}).items():
        print(f"## {name.upper()}\n{content}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--perspective", metavar="NAME",
                        help="Run single perspective analysis")
    parser.add_argument("--finding", action="store_true",
                        help="Show findings from the last audit")
    args = parser.parse_args()

    if args.perspective:
        single_perspective(args.perspective)
    elif args.finding:
        show_finding()
    else:
        full_audit()
