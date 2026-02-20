#!/usr/bin/env python3
"""
Git Auto-Sync - Morpheus AI
Skill: git-sync

Commits all workspace changes and pushes to remote.
Detects conflicts, blocks sensitive files, tags with timestamps.

Usage:
  python sync.py            # Run a full sync
  python sync.py --status   # Show git status only, no commit
"""

import sys
import os
import subprocess
import argparse
import datetime
import fnmatch

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Files/patterns that must never be committed
BLOCKED_PATTERNS = [
    ".env",
    ".env.*",
    "tokens/**",
    "tokens/",
    "*.sqlite",
    "*.db",
    "*.sqlite3",
    "*secret*",
    "*credential*",
    "*password*",
    "cookies.json",
    "*.session",
    "backups/**",
]


def run_git(args: list, cwd: str = None) -> tuple[int, str, str]:
    """Run a git command. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd or WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def is_blocked(filepath: str) -> bool:
    """Check if a file matches any blocked pattern."""
    # Normalise to forward slashes for matching
    fp = filepath.replace("\\", "/")
    fname = os.path.basename(fp)

    for pattern in BLOCKED_PATTERNS:
        if fnmatch.fnmatch(fname, pattern):
            return True
        if fnmatch.fnmatch(fp, pattern):
            return True
        # Check if path starts with a blocked directory
        if pattern.endswith("/") and fp.startswith(pattern):
            return True
        if pattern.endswith("/**") and fp.startswith(pattern[:-3]):
            return True
    return False


def get_staged_files() -> list:
    """Get list of files currently staged."""
    code, out, _ = run_git(["diff", "--cached", "--name-only"])
    if not out:
        return []
    return [f for f in out.splitlines() if f]


def get_changed_files() -> list:
    """Get list of changed/untracked files."""
    code, out, _ = run_git(["status", "--porcelain"])
    if not out:
        return []
    files = []
    for line in out.splitlines():
        if len(line) > 3:
            files.append(line[3:].strip())
    return files


def check_conflicts() -> bool:
    """Check if there are merge conflicts."""
    code, out, _ = run_git(["diff", "--name-only", "--diff-filter=U"])
    return bool(out.strip())


def show_status():
    """Show current git status."""
    code, out, err = run_git(["status", "--short"])
    branch_code, branch, _ = run_git(["branch", "--show-current"])
    remote_code, remote, _ = run_git(["remote", "get-url", "origin"])

    print(f"📋 Git Status")
    print(f"Branch: {branch}")
    print(f"Remote: {remote}")
    print()
    if out:
        print("Changed files:")
        for line in out.splitlines():
            print(f"  {line}")
    else:
        print("Working tree clean — nothing to commit.")


def run_sync():
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H-%M")
    print(f"🔄 Git Auto-Sync — {timestamp}")

    # Check we're in a git repo
    code, _, _ = run_git(["rev-parse", "--git-dir"])
    if code != 0:
        print("ERROR: Not a git repository. Run 'git init' first.")
        sys.exit(1)

    # Check for existing conflicts before doing anything
    if check_conflicts():
        print("⚠️  MERGE CONFLICT detected — manual resolution required.")
        print("Skipping sync. Resolve conflicts then run again.")
        sys.exit(1)

    # Stage all changes FIRST (so pull --rebase doesn't complain about unstaged changes)
    run_git(["add", "-A"])

    # Check for blocked files that got staged and unstage them
    staged = get_staged_files()
    blocked_found = []
    for f in staged:
        if is_blocked(f):
            blocked_found.append(f)
            run_git(["reset", "HEAD", f])
            print(f"  ⛔ Blocked (sensitive): {f}")

    if blocked_found:
        print(f"\n⚠️  {len(blocked_found)} sensitive file(s) were unstaged and will NOT be committed.")

    # Check if anything remains to commit
    staged_after = get_staged_files()
    if not staged_after:
        # Still pull to stay up to date
        run_git(["pull", "--rebase"])
        print("Nothing to commit — workspace is clean.")
        return

    # Commit local changes first
    commit_msg = f"auto-sync: {timestamp}"
    code, out, err = run_git(["commit", "-m", commit_msg])
    if code != 0:
        print(f"Commit failed: {err}")
        sys.exit(1)
    print(f"✅ Committed: {commit_msg} ({len(staged_after)} files)")

    # Now pull with rebase (local commit is safe)
    print("Pulling latest from remote...")
    code, out, err = run_git(["pull", "--rebase"])
    if code != 0:
        if "CONFLICT" in err or "conflict" in err.lower():
            print(f"⚠️  MERGE CONFLICT after pull — needs manual resolution.")
            print(f"Details: {err}")
            sys.exit(1)
        else:
            print(f"Pull warning (continuing): {err}")

    # Push
    print("Pushing to remote...")
    code, out, err = run_git(["push"])
    if code != 0:
        if "rejected" in err or "conflict" in err.lower():
            print(f"⚠️  Push rejected — possible conflict. Pull and retry.")
            print(f"Details: {err}")
            sys.exit(1)
        else:
            print(f"Push failed: {err}")
            sys.exit(1)

    print(f"✅ Pushed to remote.")

    # Tag the sync
    tag = f"auto-sync-{timestamp}"
    run_git(["tag", tag])
    run_git(["push", "origin", tag])
    print(f"🏷️  Tagged: {tag}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true", help="Show status only, no commit")
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        run_sync()
