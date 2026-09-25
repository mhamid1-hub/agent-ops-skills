#!/usr/bin/env python3
"""
watchdog_scope.py — lifecycle gate for task-scoped watchdogs.

Not a cron scheduler itself. It's the "should my poll body actually run
right now" check that any cron primitive (Hermes cronjob_manage, launchd,
systemd timer, GitHub Actions schedule, cloud scheduler) calls from inside
its job. State lives in a local JSON file — no external dependencies.

Usage:
    watchdog_scope.py activate   <job-id> [--ttl-minutes N] [--note TEXT]
    watchdog_scope.py deactivate <job-id>
    watchdog_scope.py check      <job-id>      # exit 0 = active, run the poll;
                                                # exit 1 = not active, skip it
    watchdog_scope.py list       [--all]        # active only, unless --all

Typical use inside a poll body:

    python3 scripts/watchdog_scope.py check build-check-142 || exit 0
    # ... real polling logic only below this line ...

Typical lifecycle:

    # at dispatch time
    python3 scripts/watchdog_scope.py activate build-check-142 --ttl-minutes 180 \\
        --note "watching background build for task 142"

    # once the target is confirmed done/failed/handed off
    python3 scripts/watchdog_scope.py deactivate build-check-142
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "watchdog_scope.json"


def _load():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


def cmd_activate(args):
    state = _load()
    now = _now()
    entry = {
        "activated_at": _iso(now),
        "ttl_minutes": args.ttl_minutes,
        "expires_at": _iso(now + timedelta(minutes=args.ttl_minutes)) if args.ttl_minutes else None,
        "note": args.note or "",
        "active": True,
    }
    state[args.job_id] = entry
    _save(state)
    print(f"activated {args.job_id}" + (f" (expires {entry['expires_at']})" if entry["expires_at"] else " (no TTL — set one unless you have a reason not to)"))
    return 0


def cmd_deactivate(args):
    state = _load()
    if args.job_id not in state:
        print(f"no record for {args.job_id} (already inactive or never activated)")
        return 0
    state[args.job_id]["active"] = False
    state[args.job_id]["deactivated_at"] = _iso(_now())
    _save(state)
    print(f"deactivated {args.job_id}")
    return 0


def cmd_check(args):
    state = _load()
    entry = state.get(args.job_id)
    if entry is None:
        print(f"NOT ACTIVE: {args.job_id} has no record — skip this poll", file=sys.stderr)
        return 1
    if not entry.get("active"):
        print(f"NOT ACTIVE: {args.job_id} was explicitly deactivated at {entry.get('deactivated_at')} — skip this poll", file=sys.stderr)
        return 1
    expires_at = entry.get("expires_at")
    if expires_at:
        if _now() > datetime.fromisoformat(expires_at):
            print(f"EXPIRED: {args.job_id} passed its TTL ({expires_at}) with no deactivation — treating as inactive, skip this poll", file=sys.stderr)
            entry["active"] = False
            entry["deactivated_at"] = _iso(_now())
            entry["deactivated_reason"] = "ttl_expired"
            state[args.job_id] = entry
            _save(state)
            return 1
    print(f"ACTIVE: {args.job_id} (activated {entry.get('activated_at')}" + (f", expires {expires_at}" if expires_at else ", no TTL") + ") — run the poll")
    return 0


def cmd_list(args):
    state = _load()
    if not state:
        print("(no watchdog records)")
        return 0
    now = _now()
    shown = 0
    for job_id, entry in sorted(state.items()):
        is_active = entry.get("active", False)
        expires_at = entry.get("expires_at")
        past_ttl = bool(expires_at and now > datetime.fromisoformat(expires_at))
        if not args.all and not is_active:
            continue
        shown += 1
        status = "ACTIVE"
        if not is_active:
            status = "inactive"
        elif past_ttl:
            status = "ACTIVE but PAST TTL (will self-expire on next check)"
        print(f"{job_id}: {status} | activated {entry.get('activated_at')} | expires {expires_at or 'never'} | note: {entry.get('note', '')}")
    if shown == 0:
        print("(no active watchdogs)" if not args.all else "(no records)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_activate = sub.add_parser("activate", help="mark a watchdog job as active")
    p_activate.add_argument("job_id")
    p_activate.add_argument("--ttl-minutes", type=int, default=None, help="auto-expire if never deactivated (strongly recommended)")
    p_activate.add_argument("--note", default="", help="what this watchdog is watching")
    p_activate.set_defaults(func=cmd_activate)

    p_deactivate = sub.add_parser("deactivate", help="mark a watchdog job as inactive")
    p_deactivate.add_argument("job_id")
    p_deactivate.set_defaults(func=cmd_deactivate)

    p_check = sub.add_parser("check", help="exit 0 if active (run the poll), 1 if not (skip it)")
    p_check.add_argument("job_id")
    p_check.set_defaults(func=cmd_check)

    p_list = sub.add_parser("list", help="list watchdog records")
    p_list.add_argument("--all", action="store_true", help="include inactive records too")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
