#!/usr/bin/env python3
"""Post-dispatch review of a cheap executor's output.

Runs the mechanical half of the "did the executor actually degrade honestly,
or did it fabricate a confident-looking failure state" review gate. Does NOT
replace reading the rendered values yourself — it catches the checks that are
easy to script and easy to skip under time pressure.

Usage:
    python3 review_output.py --artifact dashboard.html \
        --module compute_status.py \
        --unhappy-dates 2026-10-01,2026-10-07,2026-11-08 \
        --touched-files compute_status.py,dashboard.html

Checks:
  1. Invalid-render scan: None / nan / undefined / NaN% leaking into rendered
     output (usually from an unset variable interpolated into a template).
  2. Absent-data-as-zero heuristic: flags any comparison of an empty
     collection directly driving a "failure" branch without a `configured`/
     `has_data` guard.
  3. Unhappy-path simulation: imports a module and calls compute_bar()/
     compute_status()/main() (first one found) under monkey-patched dates,
     printing what state fires for each — you decide if it's right.
  4. Secret scan, scoped to touched files only, with placeholder awareness.
"""
import argparse
import importlib.util
import re
import sys
from datetime import date, datetime


INVALID_PATTERNS = [r"\bNone\b", r"\bnan\b", r"\bundefined\b", r"NaN%", r"width:\s*None"]

ZERO_AS_FAILURE_HEURISTIC = re.compile(
    r"if\s+(not\s+)?\w*(cache|data|results?|history)\w*\s*(==\s*\[\]|:)\s*$", re.MULTILINE
)

SECRET_PATTERNS = [
    re.compile(r"(client_secret|refresh_token|api_key)\s*[\"']?\s*[:=]\s*[\"'][^\"']{8,}", re.I),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
]
PLACEHOLDER_HINTS = ["YOUR_", "REPLACE_ME", "CHANGEME", "<", "xxx", "example"]


def scan_invalid_renders(path):
    text = open(path, errors="ignore").read()
    hits = []
    for pat in INVALID_PATTERNS:
        for m in re.finditer(pat, text):
            start = max(0, m.start() - 40)
            hits.append(text[start:m.end() + 10].replace("\n", " "))
    return hits


def scan_zero_as_failure(path):
    text = open(path, errors="ignore").read()
    hits = []
    for m in ZERO_AS_FAILURE_HEURISTIC.finditer(text):
        snippet = text[max(0, m.start() - 60):m.end()]
        if "configured" not in snippet and "has_data" not in snippet:
            hits.append(snippet.replace("\n", " ").strip())
    return hits


def scan_secrets(paths):
    findings = []
    for path in paths:
        try:
            text = open(path, errors="ignore").read()
        except FileNotFoundError:
            continue
        for pat in SECRET_PATTERNS:
            for m in pat.finditer(text):
                line = text[max(0, m.start() - 20):m.end() + 5]
                if any(h.lower() in line.lower() for h in PLACEHOLDER_HINTS):
                    continue
                findings.append((path, line.strip()))
    return findings


def simulate_unhappy_paths(module_path, dates_csv):
    if not module_path or not dates_csv:
        return
    spec = importlib.util.spec_from_file_location("audited_module", module_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"  [SKIP] could not import {module_path}: {e}")
        return

    fn = None
    for name in ("compute_bar", "compute_status", "main", "compute"):
        if hasattr(mod, name):
            fn = getattr(mod, name)
            break
    if fn is None:
        print(f"  [SKIP] no compute_bar/compute_status/main/compute() found in {module_path}")
        return

    for d in dates_csv.split(","):
        d = d.strip()
        try:
            dt = datetime.fromisoformat(d).date()
        except ValueError:
            print(f"  [SKIP] bad date {d}")
            continue
        for attr in ("TODAY", "NOW", "today"):
            if hasattr(mod, attr):
                setattr(mod, attr, dt)
        try:
            result = fn()
            print(f"  {d} -> {result}")
        except Exception as e:
            print(f"  {d} -> ERROR calling {fn.__name__}(): {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True, help="Rendered output file to scan (html/json/md/...)")
    ap.add_argument("--module", help="Python module implementing the status/compute logic, for unhappy-path sim")
    ap.add_argument("--unhappy-dates", default="", help="Comma-separated ISO dates to simulate against --module")
    ap.add_argument("--touched-files", default="", help="Comma-separated files this build touched, for secret scan")
    args = ap.parse_args()

    problems = 0

    print("== 1. Invalid-render scan ==")
    hits = scan_invalid_renders(args.artifact)
    if hits:
        problems += len(hits)
        for h in hits:
            print(f"  [BAD] ...{h}...")
    else:
        print("  clean")

    print("\n== 2. Absent-data-as-zero-performance heuristic ==")
    src_for_heuristic = args.module or args.artifact
    hits = scan_zero_as_failure(src_for_heuristic)
    if hits:
        problems += len(hits)
        for h in hits:
            print(f"  [CHECK MANUALLY] {h}  <- confirm this is gated by real fetch success, not empty-list inference")
    else:
        print("  no obvious unguarded empty-collection branches found (heuristic only — read the code too)")

    print("\n== 3. Unhappy-path simulation ==")
    if args.module and args.unhappy_dates:
        simulate_unhappy_paths(args.module, args.unhappy_dates)
    else:
        print("  (skipped — pass --module and --unhappy-dates to enable)")

    print("\n== 4. Secret scan (touched files only) ==")
    touched = [f.strip() for f in args.touched_files.split(",") if f.strip()]
    if touched:
        findings = scan_secrets(touched)
        if findings:
            problems += len(findings)
            for path, line in findings:
                print(f"  [POSSIBLE SECRET] {path}: {line}")
        else:
            print("  clean")
    else:
        print("  (skipped — pass --touched-files to enable)")

    print(f"\n{'FAIL' if problems else 'PASS'}: {problems} issue(s) found "
          f"(some items above need a human judgment call, not just this script)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
