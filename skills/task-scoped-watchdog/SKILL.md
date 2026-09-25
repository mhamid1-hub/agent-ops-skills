---
name: task-scoped-watchdog
description: "Scope monitoring crons to active work — don't poll when nothing's running."
version: 1.0.0
author: mhamid1-hub
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [cron, monitoring, watchdog, orchestration, multi-agent, cost-optimization]
  related_skills: [tiered-model-delegation]
---

# Task-Scoped Watchdog

Use when you need a recurring check on something in flight — a background
build, a dispatched subagent, a kanban task that might crash-loop — and the
obvious move is "set up a cron that polls every N minutes." Don't default to
that being always-on.

## The problem this fixes

A watchdog cron that polls forever burns cycles (API calls, tokens, wake-ups)
even when there is nothing to watch — e.g. it fires at 3am with zero active
dispatches and still runs its full check. This was a real, corrected
incident: an agent set up a permanent polling job for a one-off build check
and left it running after the build finished. The fix isn't "poll less
often," it's **scope the watchdog's lifetime to the lifetime of the thing
it watches** — active only between "I dispatched X" and "X is done, failed,
or handed off."

## When to use

- You're about to create a recurring job (cron, `process_manage` polling
  loop, a kanban crash-loop checker) whose only purpose is to watch ONE
  specific dispatch, build, or task.
- You're reviewing an existing watchdog and it's still ticking after its
  target finished.

Do **not** use this to talk yourself out of monitoring that's genuinely
needed 24/7 across many concurrent dispatches — see §3.

## Quick reference

| Watchdog lifecycle stage | Action |
|---|---|
| Before dispatch | Create the job **paused**, or don't create it yet at all |
| At dispatch (the instant the watched thing starts) | Resume/activate it |
| While watched thing is running | Let it poll |
| Watched thing confirmed done/failed/handed off | Pause or delete it immediately |
| Genuinely persistent, many concurrent targets | Get explicit sign-off for 24/7, don't default to it |

## 1. Default to paused, not running

When you create the recurring job, create it in a paused/disabled state (or
don't create it until you're about to dispatch the thing it watches). Never
create-and-immediately-run a watchdog for a target that doesn't exist yet.

Done when: the job exists (or is about to be created) with no polls firing
before there's something to poll for.

## 2. Activate only at the moment the target starts

Resume the cron / start the poll loop in the same step you dispatch the
background task, build, or subagent — not before. Use
`scripts/watchdog_scope.py activate <job-id>` to drop a scope marker your
polling logic can check, independent of whatever cron primitive you're using
(see `references/framework-adapters.md` for the exact resume/pause call per
runtime — Hermes `cronjob_manage`, launchd, systemd timers, GitHub Actions
`schedule`, cloud EventBridge/Cloud Scheduler).

```bash
python3 scripts/watchdog_scope.py activate build-check-142 --ttl-minutes 180
```

The `--ttl-minutes` flag is a safety net (see §4), not the primary
deactivation path.

## 3. Scope to ONE target unless you have sign-off for always-on

A watchdog job should watch one thing: one build, one dispatch, one task ID.
If you find yourself wanting a single job to cover "everything currently
running," that's a signal you actually need persistent monitoring — say so
explicitly to whoever owns the decision and get sign-off before making it
24/7. Don't quietly widen a task-scoped watchdog's scope to dodge the
lifecycle discipline in §1/§2/§4.

## 4. Deactivate the moment the target resolves — and have a TTL fallback

The instant the watched task/build is confirmed done, failed, or handed off,
pause or delete the job:

```bash
python3 scripts/watchdog_scope.py deactivate build-check-142
```

Prefer deleting narrowly-scoped one-off jobs entirely over leaving them
paused forever (paused clutter is still clutter you have to remember exists).

Because "remember to deactivate" is exactly the step that gets skipped under
context pressure, always set a TTL on activation (§2). Run
`scripts/watchdog_scope.py check <job-id>` from inside the polling body
itself — it exits non-zero (and prints why) once the marker is inactive OR
past its TTL, so even a forgotten deactivation self-expires instead of
polling forever:

```bash
python3 scripts/watchdog_scope.py check build-check-142 || exit 0
# ... only the real poll logic below this line ...
```

Done when: `watchdog_scope.py list` shows no active marker whose target has
already resolved, and no marker past its TTL.

## 5. Hand back

State explicitly, in whatever completion/status message you produce:
- Which watchdog(s) you created or touched, by job ID.
- Current state (active with TTL, paused, or deleted) for each.
- If you left one active, why it's still needed and when it should be
  deactivated.

## Pitfalls

- Creating the job already running because "it'll just poll and find
  nothing" — that's the exact waste this skill exists to stop.
- Forgetting to deactivate after the target finishes — always set a TTL
  (§4) so a forgotten job self-expires instead of running indefinitely.
- Widening scope from "watch this one build" to "watch everything" without
  getting explicit sign-off first (§3).
- Treating "paused forever" as equivalent to "deleted" — paused jobs still
  need to be remembered and audited; delete one-off jobs once resolved.
- Reusing one job ID across unrelated targets — `check`/`deactivate` calls
  on a reused ID can silently apply to the wrong target's state.

## Verification checklist

- The watchdog job did not fire a single poll before its target existed.
- It was activated in the same step as the target's dispatch, with a TTL.
- It was deactivated (or deleted, if one-off) within one poll cycle of the
  target resolving.
- No watchdog in `watchdog_scope.py list` is both active and past its TTL.
- Any always-on exception has an explicit recorded sign-off, not a default.

## Support files

- `scripts/watchdog_scope.py` — CLI + importable state manager: `activate`,
  `deactivate`, `check` (exit-code gate for use inside a poll body), `list`.
  Local JSON state file, no external dependencies, safe to call from any
  cron primitive as the "should I actually run my check right now" gate.
- `references/framework-adapters.md` — the exact pause/resume/delete call
  for Hermes `cronjob_manage`, macOS launchd, Linux systemd timers, GitHub
  Actions scheduled workflows, and cloud schedulers (EventBridge / Cloud
  Scheduler), plus how each wires into `watchdog_scope.py check`.
