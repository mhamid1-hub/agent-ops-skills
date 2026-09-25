---
name: kb-health-audit
description: "Use for scheduled KB health check and prompt audit runs."
version: 1.0.0
author: Hermes Agent
license: MIT
keywords: [knowledge-base, health-check, prompt-audit, cron, kb-maintenance, drift]
metadata:
  hermes:
    tags: [knowledge-base, health-check, prompt-audit, cron]
    related_skills: [kb-genesis]
---

# KB Health Audit

Generalized version of the `zero-kb-maintenance` pattern proven on Mo's `zero/`
KB, broadened to cover TWO things in one recurring pass: (1) mechanical KB
filesystem health (broken links, drift, stale figures, missing automations)
and (2) a prompt audit of the agent's own governing files (SOUL.md/system
prompt, CLAUDE.md/AGENTS.md, cron job prompts) — checking they still match
reality instead of describing a stale or aspirational state. Designed to run
on a schedule (monthly or every-2-weeks, user's choice), not just on-demand.

## When to Use

- Setting up recurring maintenance for a KB built via `kb-genesis` (or any
  existing agentic KB) — this is the skill the scheduled cron job should
  point at.
- User asks to "audit," "health check," or "tidy" the KB or its prompts,
  on-demand.
- The KB's own docs (memory/context files) claim an automation is "live"
  and that claim needs verifying, not trusting.

## Part A — Cadence Setup (do this once, at genesis or first audit)

Don't assume a cadence — ask the user explicitly:

- **Monthly** (good default for a stable KB with low daily churn)
- **Every 2 weeks** (better for a KB under active build-out, lots of new
  ingest, or one feeding a live business decision cadence)

Whichever is chosen, create it as a real scheduled job (e.g.
`cronjob_manage` action=create on Hermes) — **never leave it as a written
procedure with no actual job**, that is precisely the failure mode this
skill exists to catch elsewhere (see Part C). Hard guardrail: show the user
the exact schedule and exact prompt text before creating the job, and pin
the model/provider explicitly at creation so it doesn't silently drift when
a global default changes later. Record the job ID and cadence in the KB's
`memory.md`/`context.md` Snapshot in the same pass.

A job created via `cronjob_manage` runs in a **fresh session with no chat
context** — its prompt must be fully self-contained: point it at this skill
by name/description, name the KB root path explicitly, and state what
"done" looks like (fix everything mechanical, log judgment calls, deliver a
short summary).

## Part B — Mechanical KB Filesystem Check

Run (or write, if this KB doesn't have one yet) an entrypoint script
(`bin/check.py` pattern) that performs, at minimum:

1. **Broken links** — every relative markdown link resolves to a real file.
   Watch cross-domain link traps (a topic split across two domain folders
   needs the full relative path, not a bare filename).
2. **Orphaned pages** — every wiki page is linked from `index.md` (or
   another live page); nothing exists with zero inbound links.
3. **Facts Registry drift** — diff numbers quoted in wiki pages against
   `wiki/data/facts.yml`; flag mismatches. `facts.yml` is upstream of prose
   by design (see `kb-genesis`) — a mismatch means prose wasn't updated
   after a figure changed there.
4. **Retired-figure leakage** — scan live pages + context files for any
   number listed in `facts.yml`'s `retired:` block that appears outside its
   `allowed_in` allowlist. A hit is either legitimate history (add the file
   to the allowlist) or a genuine stale claim (fix the number).
5. **Dependency Graph staleness** — read `wiki/data/dependencies.yml`; flag
   any downstream page that hasn't been touched since its listed upstream
   dependency last changed.
6. **Log discipline** — `log.md` is a rolling index only; graduate old rows
   into topic memory files only after confirming the content already lives
   there (grep don't assume), never delete unpreserved content.
7. **Context budget/freshness** — if the KB has a `context.md` (or
   equivalent always-read-first file), check it against its token budget;
   trim in sized batches, not one clause per re-check cycle, and estimate
   the deficit up front rather than trickling under the limit.
8. **Dashboard sync** (if the KB has one) — static file and any live
   artifact surface don't share a data source; a figure changed in one must
   be hand-mirrored to the other in the same pass. Recompute and update any
   sync-hash markers after regenerating.

**Fix what's found, don't just report it.** Re-run the check after fixing to
confirm clean before declaring the pass done.

### Judgment-call backlog

Anything that isn't a mechanical fix (an orphaned page that might be worth
keeping, a style inconsistency, a "should this get its own page" call)
goes into a persistent `_review/health-check-backlog.md`, not a one-shot
report that gets forgotten. Append under `## Open` with the date and which
run found it; close items by moving to `## Resolved` (with fix + date) or
`## Wontfix` (only with a specific reason the user actually agreed to).
Check existing Open items before adding a duplicate.

## Part C — Prompt Audit (the agent's own governing files)

This is the piece most KB health-check patterns skip: the agent auditing
its OWN instructions, not just the data it maintains. Three passes:

1. **Content-vs-loaded-context diff.** Read the agent's actual system
   prompt / persona file (SOUL.md or equivalent) from disk and diff it
   against what's genuinely loaded in the current session's context. A
   mismatch means the running agent and the file on disk have drifted —
   flag exactly what differs.
2. **Internal consistency.** Does the prompt contradict itself (routing
   rules that point two different ways, constraints listed in one section
   the "autonomous" list elsewhere silently violates)?
3. **Claims-vs-reality verification — the highest-value check.** Any
   sentence in a governing file asserting something is "done," "retired,"
   "live," "migrated," or "stopped" is a claim, not a fact, until checked
   against the actual running system:
   - A profile/service claimed "retired" — check for a live process
     (`ps aux | grep <name>`), not just the absence of new activity.
   - A gateway/job claimed "stopped" — check for a supervisor (launchd
     plist, systemd unit, container restart policy) that would silently
     respawn it; killing the process without disabling the supervisor is
     an incomplete fix.
   - A cron/automation claimed "scheduled" — list the actual scheduled
     jobs and confirm it exists; a KB's own docs describing something as
     live is not evidence it was ever created (this is the single most
     common gap found in practice — a skill/procedure gets fully written
     and then never actually wired to a scheduler).
   - A migration claimed "complete" — check every artifact the migration
     said it would touch (old process killed AND its supervisor disabled
     AND cron jobs re-pointed AND docs updated), not just the most visible
     one.

**Fix don't just flag** — if Part C finds a live-but-claimed-dead process,
kill it (escalate SIGTERM → SIGKILL if a supervisor respawns it, then
disable the supervisor itself) and correct the file's claim in the same
pass, same standard as Part B's "fix what's found."

## Part D — Delivery

End every audit run (scheduled or on-demand) with a short, concrete summary:
what was checked, what was found broken and fixed, what's sitting in the
judgment-call backlog, and what (if anything) needs the user's decision.
A clean run still gets a one-line "checked, nothing wrong" — silence after
a scheduled audit reads as "did it even run," not as "all clear."

## Pitfalls

- **"The docs say it's live" is never sufficient evidence** — this is the
  single repeated failure mode behind this skill (see Part C, item 3).
  Every "is this actually happening" question gets a filesystem/process
  check, not a memory-file read.
- **A killed process can come back** if a supervisor manages it (launchd,
  systemd, a container orchestrator, PM2). Confirm the process is gone
  AND find/disable whatever would restart it — checking only the process
  list right after killing it produces a false-clean result.
- **Don't let a scheduled audit job silently drop scope over time.** If
  the cron job's prompt was written once and the KB has since grown new
  domains/files, the audit needs updating too — review the job's own
  prompt text against the current KB structure occasionally, the same
  skepticism this skill applies to everything else.

## See Also

- `kb-genesis` — the KB-creation counterpart; a fresh KB should pass this
  audit clean on its first run (see `kb-genesis` Step 8).
