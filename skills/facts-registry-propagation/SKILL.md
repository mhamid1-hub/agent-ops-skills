---
name: facts-registry-propagation
description: "Use when a KB fact changes; propagate it everywhere."
version: 1.0.0
author: Hermes Agent
license: MIT
keywords: [knowledge-base, facts-registry, propagation, drift, data-integrity, kb-genesis]
metadata:
  hermes:
    tags: [knowledge-base, facts-registry, drift-prevention]
    related_skills: [kb-genesis, kb-health-audit]
---

# Facts Registry Propagation

Runs the exact update chain whenever a figure tracked in a KB's facts
registry (`wiki/data/facts.yml` or equivalent) changes — a debt paid down, a
new deadline, a balance confirmed, a follower count, an invoice total, a
revenue number. Distilled from a real incident: before this discipline
existed, one KB had the same handful of figures duplicated across ~12 wiki
pages plus a dashboard with no mechanism to keep them in sync, and two live
pages were later found still quoting superseded numbers months after the
real figure had changed. `kb-genesis` tells you to build a facts registry;
this skill is the part that was missing — the actual propagation procedure
for when a tracked figure moves, so the registry doesn't silently rot into
just another place the number lives, out of sync with everywhere else.

## When to use

- A figure that already exists in the KB's facts registry changes (reported
  directly, or discovered during an ingest/scan pass).
- `kb-health-audit`'s drift check flags a figure that no longer matches its
  registry entry — this skill is how you fix it, not just flag it again.

## When NOT to use

- The figure appears in exactly one place and isn't dashboard-feeding. Edit
  that one page directly and skip the registry entirely — a one-off number
  forced into the registry is clutter, not rigor. Only promote a figure into
  the registry once it appears in 2+ places or feeds a dashboard/summary.
- You're building the registry for the first time — that's `kb-genesis`
  Step 5 (seeding), not this skill (updating an existing entry).

## The chain, in order

1. **Update the registry's value** to the new figure.

2. **Add the old value to the registry's `retired:` block**, with a tight
   `allowed_in` allowlist — only pages where the old number is legitimately
   historical (a revision-history table, a "was X, now Y" sentence). Keep
   the allowlist as narrow as possible; a broad one quietly turns off the
   health-audit's ability to catch drift on this figure going forward.
   **This step is the entire upkeep of the registry — skip it and the
   drift check silently stops covering this figure forever, not just this
   once.**

3. **Propagate the new figure to every wiki page that quotes the old one.**
   Grep for the old value across the wiki tree to find them all, e.g.:
   ```bash
   grep -rn "OLD_VALUE" wiki --include="*.md"
   ```
   Exclude rolling logs, log archives, and any dated `*-memory.md` files from
   this pass — those are historical records where the old figure is correct
   by design, and the health-audit deliberately doesn't scan them either.
   Decide and document this exclusion list once, in the governing file, so
   every future propagation pass (human or agent) uses the same list instead
   of re-deciding it ad hoc.

4. **If this metric has an append-only history file** (a `metric-history.yml`
   or equivalent tracking dated snapshots over time), **append one new dated
   point** to the matching series. Never edit or delete a past point — this
   file is append-only by design; editing history defeats its entire purpose.
   A metric only earns a place in the history file once 2+ dated snapshots
   genuinely exist or will keep accumulating — don't start a new series for
   a one-off change.

5. **If this change is dashboard-worthy** (new urgent item, a section's
   figures changed, a new card warranted): update every dashboard surface —
   a static file AND any live chat-platform artifact mirroring it — **in
   the same pass, from the same source content**. Never update one surface
   and leave the other; two dashboards with no shared data source drift
   silently the moment only one gets remembered. If the governing file
   defines a sync marker (a hash, a timestamp) between the registry and the
   dashboard, update it as part of this step, not as an afterthought.

6. **If the fact belongs to a topic with its own memory file** (a project's
   `memory.md`, a case-specific memory page), add a dated entry there
   describing what changed and why. If it's cross-cutting rather than
   single-topic, add a one-line pointer row to the KB's rolling log index
   instead — follow whatever log-discipline rule the governing file states.

7. **Run the KB's mechanical health check** at the end and confirm the
   facts-drift check, the retired-figure-leakage check, and the
   dashboard-vs-registry-sync check (whatever they're numbered/named in this
   KB's `kb-health-audit` setup) all come back clean before considering this
   done. A propagation pass that skips its own verification is exactly the
   kind of silent-drift failure this skill exists to prevent.

## Sensitive figures

If the changed figure is a sensitive number (an ID number, passport, account
number, exact salary, anything the KB's sensitivity rules flag) — check with
the user case-by-case before writing the actual value anywhere, including
the registry itself. Default to a prose description and a pointer to the
source document rather than the literal figure.

## Pitfalls

- **Treating the registry as "done" once it exists.** A registry that's
  never updated when its figures change is worse than no registry — it's a
  stale source of truth people trust by default. The registry's value is
  entirely in this propagation discipline, not in its existence.
- **Skipping the `retired:` allowlist step "because it's extra work."** This
  is the step that was skipped in the originating incident, and it's exactly
  what let two live pages keep quoting a superseded figure for months —
  nothing else in the chain would have caught it once this step was skipped.
- **Updating the dashboard and the registry in separate passes "to save
  time."** They will drift the next time only one gets remembered; do them
  in the same pass or not at all this cycle.
- **Promoting every figure into the registry "to be safe."** A registry
  bloated with one-off numbers that never duplicate anywhere makes the real
  propagation targets harder to find. Keep the bar at 2+ locations or
  dashboard-feeding, per the "When NOT to use" section above.

## See Also

- `kb-genesis` — seeds the registry structure at KB creation time (Step 5);
  this skill is what runs every time after that, when a seeded figure moves.
- `kb-health-audit` — the periodic check that catches drift if this chain
  was skipped or ran incomplete; treat its findings as a trigger to run this
  skill properly, not just to patch the one flagged page.
