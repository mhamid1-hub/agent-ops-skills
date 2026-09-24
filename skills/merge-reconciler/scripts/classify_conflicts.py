#!/usr/bin/env python3
"""Extract and classify every git conflict-marker block in a repo.

Usage:
    # List all conflicts with a suggested classification hint
    python3 classify_conflicts.py --repo /path/to/repo

    # After resolving, verify no markers remain (exit 0 = clean)
    python3 classify_conflicts.py --repo /path/to/repo --check

This does NOT resolve anything — it removes the risk of missing a hunk by
eyeballing `git diff` output, and gives you both sides' text side by side so
you can classify against the stated intents (see SKILL.md §2-3).
"""
import argparse
import os
import re
import sys

MARKER_START = re.compile(r"^<{7} (.*)$")
MARKER_MID = re.compile(r"^={7}$")
MARKER_END = re.compile(r"^>{7} (.*)$")

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def find_conflicted_files(repo):
    hits = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            path = os.path.join(root, fname)
            try:
                with open(path, "r", errors="ignore") as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            if "<<<<<<<" in text and "=======" in text and ">>>>>>>" in text:
                hits.append(path)
    return hits


def extract_hunks(path):
    """Return list of (start_line, end_line, ours_label, ours_text, theirs_label, theirs_text)."""
    hunks = []
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        m_start = MARKER_START.match(lines[i].rstrip("\n"))
        if not m_start:
            i += 1
            continue
        start_line = i + 1
        ours_label = m_start.group(1)
        ours = []
        i += 1
        while i < len(lines) and not MARKER_MID.match(lines[i].rstrip("\n")):
            ours.append(lines[i])
            i += 1
        i += 1  # skip =======
        theirs = []
        while i < len(lines) and not MARKER_END.match(lines[i].rstrip("\n")):
            theirs.append(lines[i])
            i += 1
        m_end = MARKER_END.match(lines[i].rstrip("\n")) if i < len(lines) else None
        theirs_label = m_end.group(1) if m_end else "?"
        end_line = i + 1
        i += 1
        hunks.append((start_line, end_line, ours_label, "".join(ours), theirs_label, "".join(theirs)))
    return hunks


def suggest_class(ours_text, theirs_text):
    ours_norm = re.sub(r"\s+", " ", ours_text).strip()
    theirs_norm = re.sub(r"\s+", " ", theirs_text).strip()
    if ours_norm == theirs_norm:
        return "identical-after-normalization (likely whitespace-only; verify then keep either)"
    if not ours_norm or not theirs_norm:
        return "superseded? (one side is empty — check if it deleted something the other still needs)"
    # crude line-overlap heuristic
    ours_lines = set(l.strip() for l in ours_text.splitlines() if l.strip())
    theirs_lines = set(l.strip() for l in theirs_text.splitlines() if l.strip())
    overlap = ours_lines & theirs_lines
    if not overlap:
        return "disjoint-intent? (no shared lines — likely combine both)"
    return "same-question-different-answer? (overlapping content, different resolution — pick one per stated intent)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo root to scan")
    ap.add_argument("--check", action="store_true",
                     help="Just verify zero conflict markers remain; exit 1 if any found")
    args = ap.parse_args()

    files = find_conflicted_files(args.repo)

    if args.check:
        if files:
            print(f"FAIL: conflict markers still present in {len(files)} file(s):")
            for f in files:
                print(f"  {f}")
            sys.exit(1)
        print("PASS: no conflict markers found")
        sys.exit(0)

    if not files:
        print("No conflicted files found (looked for <<<<<<< / ======= / >>>>>>> markers).")
        return

    total_hunks = 0
    for path in files:
        hunks = extract_hunks(path)
        total_hunks += len(hunks)
        print(f"\n{'='*70}\n{path}  ({len(hunks)} hunk(s))\n{'='*70}")
        for idx, (start, end, ours_label, ours_text, theirs_label, theirs_text) in enumerate(hunks, 1):
            print(f"\n--- Hunk {idx} (lines {start}-{end}) ---")
            print(f"[OURS: {ours_label}]")
            print(ours_text.rstrip() or "(empty)")
            print(f"[THEIRS: {theirs_label}]")
            print(theirs_text.rstrip() or "(empty)")
            print(f"Suggested class: {suggest_class(ours_text, theirs_text)}")

    print(f"\n{'—'*70}\nTotal: {len(files)} file(s), {total_hunks} hunk(s). "
          f"Classify each against the STATED INTENTS (SKILL.md §1-2), not this heuristic alone.")


if __name__ == "__main__":
    main()
