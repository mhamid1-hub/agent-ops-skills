#!/usr/bin/env python3
"""Pre-dispatch audit of a planner's roadmap/plan before handing it to a
cheap executor model.

Checks:
  1. References to keys/paths in a named data file (yaml/json) that don't
     actually exist there.
  2. Literal values in the plan that match values you told it to READ from
     a source of truth instead of hardcoding (duplicate-of-brief detector).

Usage:
    python3 audit_roadmap.py --roadmap plan.md \
        --data-file facts.yml \
        --literals "45=personal.monthly_target_pct,530=personal.year_target"

Exit code 0 if clean, 1 if any MISSING key or unresolved literal is found
(useful in CI / pre-dispatch gating scripts).
"""
import argparse
import json
import re
import sys


def load_data_file(path):
    if path is None:
        return {}
    with open(path) as f:
        text = f.read()
    try:
        import yaml  # optional dependency
        return yaml.safe_load(text) or {}
    except ImportError:
        pass
    try:
        return json.loads(text)
    except Exception:
        print(f"WARN: could not parse {path} as YAML or JSON (install pyyaml "
              f"for YAML support); skipping key-existence checks", file=sys.stderr)
        return {}


def dotted_get(data, dotted_key):
    node = data
    for part in dotted_key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None, False
    return node, True


KEY_PATTERNS = [
    # facts["a"]["b"], facts['a']['b']
    re.compile(r"""\w+\[['"](\w+)['"]\]\[['"](\w+)['"]\]"""),
    # data.get("a.b") / config.get('a.b')
    re.compile(r"""\w+\.get\(['"]([\w.]+)['"]\)"""),
]


def find_referenced_keys(text):
    keys = set()
    for pat in KEY_PATTERNS:
        for m in pat.finditer(text):
            groups = m.groups()
            if len(groups) == 2:
                keys.add(f"{groups[0]}.{groups[1]}")
            elif len(groups) == 1:
                keys.add(groups[0])
    return sorted(keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roadmap", required=True, help="Path to the plan/roadmap markdown or text file")
    ap.add_argument("--data-file", help="YAML/JSON source of truth the plan is expected to read from")
    ap.add_argument("--repo", default=".", help="Repo root, for future file-path existence checks")
    ap.add_argument(
        "--literals",
        default="",
        help="Comma-separated literal=dotted.key pairs the plan should be reading, "
             "e.g. '45=personal.monthly_target_pct,530=personal.year_target'",
    )
    args = ap.parse_args()

    text = open(args.roadmap).read()
    data = load_data_file(args.data_file)

    problems = 0

    print("== Key/path existence check ==")
    refs = find_referenced_keys(text)
    if not refs:
        print("  (no dotted/bracket key references detected — pattern may need "
              "extending for this plan's access style)")
    for key in refs:
        _, ok = dotted_get(data, key) if data else (None, None)
        if data:
            status = "OK" if ok else "MISSING"
            if not ok:
                problems += 1
            print(f"  [{status}] {key}")
        else:
            print(f"  [SKIP - no --data-file given] {key}")

    print("\n== Hardcoded-literal-vs-source-of-truth check ==")
    if args.literals:
        pairs = [p.split("=", 1) for p in args.literals.split(",") if "=" in p]
        for literal, dotted_key in pairs:
            literal = literal.strip()
            dotted_key = dotted_key.strip()
            found_literal = re.search(rf"(?<![\w.]){re.escape(literal)}(?![\w.])", text)
            value, ok = dotted_get(data, dotted_key) if data else (None, None)
            if found_literal:
                problems += 1
                print(f"  [HARDCODED] literal '{literal}' appears in plan verbatim; "
                      f"should read '{dotted_key}'" +
                      (f" (current value: {value})" if ok else " (WARNING: key also missing from data file!)"))
            else:
                print(f"  [OK] literal '{literal}' not found hardcoded; presumably read from '{dotted_key}'")
    else:
        print("  (no --literals given — skipping)")

    print(f"\n{'FAIL' if problems else 'PASS'}: {problems} issue(s) found")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
