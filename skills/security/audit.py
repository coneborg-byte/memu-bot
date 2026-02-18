#!/usr/bin/env python3
"""
Security Audit - Morpheus AI
Skill: security

Analyses the workspace codebase from four perspectives using local Ollama.
Produces a numbered findings report.

Usage:
  python audit.py                          # Full audit (all 4 perspectives)
  python audit.py --perspective offensive  # Single perspective
  python audit.py --finding 3             # Detail on finding #3
"""

import sys
import os
import json
import glob
import argparse
import requests
import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "llama3.1:8b"
FINDINGS_FILE = os.path.join(WORKSPACE, "memory", "security-findings.json")

PERSPECTIVES = {
    "offensive":    "You are a penetration tester. What could an attacker exploit in this code? Look for: hardcoded secrets, injection vulnerabilities, exposed endpoints, insecure dependencies, path traversal risks.",
    "defensive":    "You are a defensive security engineer. Are protections adequate? Look for: input validation, error handling that leaks info, missing auth checks, insecure defaults, logging of sensitive data.",
    "privacy":      "You are a data privacy auditor. Is sensitive data handled correctly? Look for: credentials in code, PII in logs, unencrypted storage of secrets, data sent to unexpected destinations.",
    "operational":  "You are a pragmatic security reviewer. Are security measures practical or just theatre? Look for: security controls that are disabled, overly complex auth that gets bypassed, configs that contradict each other.",
}

# File extensions to scan
SCAN_EXTENSIONS = [".py", ".js", ".ts", ".json", ".env", ".md", ".sh", ".bat"]
# Paths to skip
SKIP_DIRS = {"temp_openclaw", ".git", "__pycache__", "node_modules", "docs", "init", ".pi"}


def collect_files():
    """Collect all relevant source files from the workspace."""
    files = []
    for root, dirs, filenames in os.walk(WORKSPACE):
        # Skip unwanted directories
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
    import re
    # Redact tokens/keys that look like secrets
    text = re.sub(r'(token|key|secret|password|apikey)\s*[=:]\s*["\']?[\w\-\.]{10,}["\']?',
                  r'\1=***REDACTED***', text, flags=re.IGNORECASE)
    return text


def run_perspective(name: str, description: str, files: list) -> list:
    """Run one security perspective across all files. Returns list of findings."""
    print(f"\n[{name.upper()}] Analysing {len(files)} files...", file=sys.stderr)

    # Build a condensed view of the codebase for the model
    codebase_summary = []
    for rel, fpath in files[:20]:  # Limit to 20 most relevant files
        content = read_file_safe(fpath, max_chars=500)
        codebase_summary.append(f"=== {rel} ===\n{content}")

    codebase_text = "\n\n".join(codebase_summary)

    prompt = (
        f"{description}\n\n"
        f"Review this codebase and list your top findings as a numbered list.\n"
        f"For each finding: severity (CRITICAL/HIGH/MEDIUM/LOW), location, and what the risk is.\n"
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
        result = resp.json().get("response", "").strip()
        return result
    except Exception as e:
        return f"[error running {name} perspective: {e}]"


def full_audit():
    files = collect_files()
    print(f"🔍 Security Audit — {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Scanning {len(files)} files across 4 perspectives...\n")

    all_findings = {}
    finding_num = 1
    report_lines = [
        f"🛡️ Security Audit Report",
        f"Date: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Files scanned: {len(files)}",
        ""
    ]

    for name, description in PERSPECTIVES.items():
        result = run_perspective(name, description, files)
        result = redact_secrets(result)
        report_lines.append(f"## {name.upper()}")
        report_lines.append(result)
        report_lines.append("")
        all_findings[name] = result

    # Save findings for --finding lookup
    os.makedirs(os.path.dirname(FINDINGS_FILE), exist_ok=True)
    with open(FINDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "findings": all_findings
        }, f, indent=2, ensure_ascii=False)

    print("\n".join(report_lines))


def single_perspective(name: str):
    if name not in PERSPECTIVES:
        print(f"Unknown perspective: {name}. Choose from: {', '.join(PERSPECTIVES.keys())}")
        sys.exit(1)
    files = collect_files()
    result = run_perspective(name, PERSPECTIVES[name], files)
    result = redact_secrets(result)
    print(f"🛡️ {name.upper()} Perspective\n")
    print(result)


def show_finding(num: int):
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
                        help=f"Run single perspective: {', '.join(PERSPECTIVES.keys())}")
    parser.add_argument("--finding", metavar="N", type=int,
                        help="Show details of finding number N from last audit")
    args = parser.parse_args()

    if args.perspective:
        single_perspective(args.perspective)
    elif args.finding:
        show_finding(args.finding)
    else:
        full_audit()
