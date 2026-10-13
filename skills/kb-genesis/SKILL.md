---
name: kb-genesis
description: "Use when building a new KB. Onboard user, then scaffold it."
version: 1.1.0
author: Hermes Agent
license: MIT
keywords: [knowledge-base, onboarding, filesystem, kb-genesis, wiki, facts-registry, scaffolding, roadmap]
metadata:
  hermes:
    tags: [knowledge-base, onboarding, scaffolding, kb-genesis]
    related_skills: [kb-health-audit, facts-registry-propagation]
---

# KB Genesis

Stands up a brand-new agentic knowledge-base filesystem from a bare directory
(or nothing at all) to a fully active, self-maintaining KB — the same pattern
proven on Mo's `zero/` KB, generalized so it works for anyone/any domain set.
Don't freelance a structure from scratch each time; this is the reusable
procedure, refined with a proper onboarding interview instead of guessing at
the user's domains and sensitivity rules.

## When to Use

- User asks to "set up a knowledge base," "build me a wiki/second-brain,"
  "do what zero does but for X," or hands you a pile of raw documents/notes
  with no existing structure.
- A prior KB exists but is informal (a flat notes folder, no facts registry,
  no permission table) and the user wants it formalized.

Do **not** use this to add one page to an already-scaffolded KB — that's
normal ingest work, not genesis.

## Step 0 — Onboarding Interview (mandatory, batched)

Never scaffold blind. Before creating a single file, ask the user (one
batched multi-question prompt, not five separate round-trips):

1. **Domains** — what top-level subject areas does this KB need to cover?
   (e.g. Legal, Finance, Career, Marketing, Health — whatever fits). Offer
   the zero-proven default set as a suggested starting point, not a mandate.
2. **Personal vs. Business split** — does every domain need both, or is this
   a single-context KB (all-personal or all-business)? Don't assume the
   Personal/Business split if the user only has one context.
3. **Existing raw material** — where does source material already live
   (folders, email, a note app, screenshots)? This determines the first
   ingest pass, not just the scaffold.
4. **Sensitivity rules** — any categories of data (IDs, account numbers,
   health details, salary) that need case-by-case confirmation before being
   written into wiki prose, vs. fine to store directly?
5. **Automation cadence** — does the user want scheduled ingestion (daily
   morning scan, nightly maintenance) from day one, or manual/conversational
   triggers only for now? If scheduled: exact time and what sources to pull
   from (mail, bank, social, calendar) — get concrete, not "sometime in the
   morning."
6. **Platform** — is this read/edited by a human too (Obsidian vault, plain
   folder, synced via iCloud/Dropbox), or agent-only? Affects file-permission
   quirks (see Pitfalls) and whether to add `.obsidian` config.

Don't proceed to Step 1 until these are answered — the scaffold decisions
below all depend on the answers.

## Step 0.5 — Goal-Clarifying Questions (mandatory, same batch as Step 0)

Domains and sensitivity tell you *what* to build. They don't tell you *why*,
and without the why, genesis produces a tidy folder tree nobody ever opens
again. Borrowed from the `appbuild` skill's Discovery phase — a KB is a
product too, and it needs the same "what does done look like" rigor a
beginner's app idea gets before any scaffolding happens. Ask these in the
same batched prompt as Step 0, not a second round-trip:

1. **The one-sentence job** — what decision or recurring question is this KB
   supposed to make easier? ("Never lose track of who owes who what,"
   "stop re-explaining my health history to every new doctor," "one place
   that knows the whole company's numbers.") If the answer is vague ("just
   organize my stuff"), push for the concrete moment it'll get used — a
   KB with no identified use-moment gets abandoned within weeks.
2. **Success criteria at 90 days** — what does "this is working" actually
   look like? (Zero missed renewal dates, one weekly briefing instead of
   five scattered checks, a question answered from the KB instead of
   re-researched from scratch.) This becomes the roadmap's north star in
   Step 1.5 — write it down verbatim, don't paraphrase it into something
   vaguer.
3. **Rollout horizon** — quick scaffold-and-go in one sitting, or a phased
   build (scaffold this week, ingest month 1, automation month 2)? This sets
   the roadmap's phase boundaries, not just a nice-to-have timeline.
4. **Who else touches it** — agent-only, or does a human read/edit pages too
   (changes review/approval expectations) and does anyone besides the
   requester need access (changes the Permission Table's scope in Step 3)?

Don't skip this because Step 0 already feels like enough questions — Step 0
tells you the shape, Step 0.5 tells you whether the shape is worth building.
A KB scaffolded on "organize my stuff" with no named success criterion is
functionally unroadmappable: every future session has to re-derive what
"done" means from nothing.

## Step 1 — Scaffold the Directory Structure

Create (adapting names to the user's actual domain list from Step 0):

```
<kb-root>/
  sources/                  # raw, NEVER-edited original material, per project/domain
  wiki/
    <domain-1>/[personal/|business/]
    <domain-2>/[personal/|business/]
    data/
      facts.yml             # single source of truth for cross-referenced figures
      dependencies.yml      # which pages depend on which
      metric-history.yml    # append-only time series (only if tracking trends)
    index.md                # front door — links every domain
    log.md                  # short rolling index of recent cross-cutting entries
  projects/                 # living trackers, each optionally with its own memory.md
  outputs/                  # answers/reports generated from real questions asked against the KB
  _review/                  # flagged items awaiting the user's decision — nothing auto-deletes here
  About me/ (or Profile/)
    about-me.md
    memory.md               # dated entries + a current "Snapshot" section, read every session
    writing-style.md        # optional, if the KB drafts content in the user's voice
  routines/                 # only if Step 0 asked for scheduled automation
    cache/
    data/
  bin/
    check.py                # entrypoint for the health-check pass (see kb-health-audit skill)
```

Omit `Personal/`+`Business/` sub-splits entirely if Step 0 said single-context
— don't build unused scaffolding.

## Step 1.5 — Write the KB Roadmap

Write `ROADMAP.md` at the KB root, checklist-style, exactly like `appbuild`
does for an app build — this is the single artifact that turns "I scaffolded
some folders" into "here's the plan and here's how far along it is." Fill
it from the Step 0 / Step 0.5 answers, don't leave it generic:

```markdown
# Roadmap: <KB name>

**North star (Step 0.5 success criteria, verbatim):** <...>
**Rollout horizon:** <quick / phased — and if phased, the phase dates>

## Phase A — Scaffold
- [ ] Directory structure created (Step 1)
- [ ] Governing file written (Step 2)
- [ ] Profile files seeded (Step 3)

## Phase B — First Ingest
- [ ] Raw material copied into sources/ per domain
- [ ] First wiki pages synthesized and linked from index.md
- [ ] facts.yml / dependencies.yml seeded from real figures (not stubs)

## Phase C — Automation (skip entirely if Step 0 said manual-only)
- [ ] Scheduled job(s) created — exact schedule + prompt text confirmed with user
- [ ] First scheduled run completed and verified (not just "created")

## Phase D — Steady State
- [ ] First kb-health-audit pass clean
- [ ] Maintenance cadence agreed (who runs it, how often)
- [ ] Re-check against North star: does the KB actually answer the Step 0.5 job yet?
```

Show this roadmap to the user before Step 2 — same rule `appbuild` uses for
its own ROADMAP.md: a plan the user hasn't seen and approved is a plan where
the first thing they notice is unexplained files appearing. Update the
checkboxes as later steps complete; a roadmap written once and never touched
again is just a to-do list that lied about being a roadmap.

## Step 2 — Write the Governing Instructions File

Create `claude.md`/`AGENTS.md`/`CLAUDE.md` (match whatever the user's agent
runtime reads) at the KB root, covering — this is the file every future
session reads to know how to maintain the KB, don't skip sections to save
time:

1. **Structure** — what each folder is for, in the user's own domain terms.
2. **Facts Registry rule** — `wiki/data/facts.yml` is upstream of prose. Any
   tracked figure that changes gets updated there FIRST, the old value moved
   to a `retired:` block with an `allowed_in` allowlist, THEN propagated to
   wiki pages. This exists because duplicated figures drift silently
   otherwise — don't skip it thinking it's premature for a small KB; add it
   at genesis, it's cheap now and expensive to retrofit after 50 pages. Point
   at the `facts-registry-propagation` skill as the exact update chain to
   run whenever a tracked figure changes, rather than re-deriving it here.
3. **Dependency Graph rule** — `wiki/data/dependencies.yml` records
   upstream/downstream pages; an upstream change means downstream pages get
   re-checked, not assumed still accurate.
4. **Permission Table** — a concrete per-domain table: what the agent can do
   without asking vs. what always needs the user's sign-off. Populate this
   from Step 0's sensitivity answers and Step 0.5's "who else touches it"
   answer — this is the single most commonly-skipped section and the one
   that prevents an agent from overstepping later (sending something
   externally, committing the user to a decision, etc).
5. **Log discipline** — `log.md` is a rolling index only; entries graduate
   into topic memory files once confirmed preserved there, never deleted
   before that check.
6. **Sensitive data rule** — restate Step 0's answer as an explicit rule,
   not left implicit.
7. **The Ongoing Loop** — INGEST (new source material in → wiki updated,
   linked, memory entry added) / ANSWER (question asked → saved to
   `outputs/`) / TIDY (periodic health check — point at the `kb-health-audit`
   skill rather than re-deriving the checklist here).

## Step 3 — Populate the Profile Files

- `about-me.md` — static facts about the user (from the onboarding answers
  plus anything else they volunteer).
- `memory.md` — start with an empty dated-entries log and a `## Snapshot`
  header (even if the Snapshot is currently just placeholder bullets per
  domain) — this is what every session reads first, so its shape matters
  from day one more than its initial content.
- `writing-style.md` — only if the KB will draft content in the user's voice.

## Step 4 — First Ingest Pass (if raw material exists)

If Step 0 identified existing raw material: copy/link it into `sources/`
(never edit the source), then synthesize the first wiki pages from it,
linking them into `index.md`. Don't leave `sources/` populated with nothing
reflected in `wiki/` — that's a KB that looks empty despite having input.
Tick off the matching Phase B boxes in `ROADMAP.md` as this completes.

## Step 5 — Seed the Registries

Even with only a handful of pages, seed `facts.yml` and `dependencies.yml`
with whatever cross-referenced figures/relationships already exist from
Step 4's ingest — don't leave them as empty stub files waiting for a future
pass. An empty registry with no habit of using it never gets used later.

## Step 6 — Dashboard (optional, ask first)

Only build a dashboard (static HTML, or a live artifact) if the user
actually wants an at-a-glance view — don't default to building one. If they
do, and there will be two surfaces (a static file plus a live chat-platform
artifact), write the two-surface sync rule into the governing file from
Step 2 explicitly (they have no shared data source and will drift silently
if only one gets remembered on each future edit).

## Step 7 — Scheduled Automation (only if Step 0 asked for it)

Use the platform's scheduler (e.g. `cronjob_manage` on Hermes) to create the
ingestion routine(s) the user specified. **Hard guardrail, not optional:**
show the user the exact schedule and exact prompt text before creating any
scheduled job — never create-and-tell. Pin the model/provider explicitly at
creation rather than leaving it to inherit a global default that can change
underneath it later.

If the user instead wants a conversational trigger ("run the morning scan
when I say good morning") rather than a hard cron, write that trigger
explicitly into the governing file from Step 2 — a trigger that lives only
in someone's head is a trigger that gets forgotten.

## Step 8 — Verification Pass

Before declaring genesis complete, run the `kb-health-audit` skill's
mechanical filesystem check against the freshly built KB. A newly scaffolded
KB should come back clean; if it doesn't (a broken link in the very first
seeded pages, a facts.yml entry that doesn't match a wiki page), fix it
before handoff — don't ship a KB whose first health check already fails.

## Step 9 — Handoff Summary

End with a concrete, concise summary: what got created (folder tree), what
got ingested (if anything), what automation (if any) is now scheduled and
when it next fires, and — critically — what the user needs to do next
(e.g. "drop your first source documents into `sources/legal/` and say
'ingest'"). Point at `ROADMAP.md` as the living tracker rather than
re-listing every checkbox in prose. A genesis pass that ends in silence
leaves the user unsure if anything actually happened.

## Pitfalls (carried over from real KB-genesis experience)

- **Cloud-synced folders can silently block shell scripts.** If the KB lives
  under an iCloud/Dropbox/OneDrive-synced path, a runtime's execution guard
  may fail closed on `.sh` files stored there with no error output — it just
  looks like the script did nothing. If you hit a "script produces zero
  output" mystery in a synced folder, suspect this before assuming a logic
  bug; keep the real script logic outside the synced path and leave a thin
  wrapper (e.g. a `.py` file that subprocess-execs the real script) inside
  the synced folder pointing at it.
- **Cross-domain relative links are a common day-one mistake** when a topic
  spans two domain folders (e.g. a business venture with both a marketing
  page and a finance page) — a bare filename link looks right but resolves
  wrong. Verify every cross-domain link actually resolves rather than
  assuming; a quick find+grep sweep catches this class of bug in one pass
  instead of one broken link at a time.
- **An onboarding interview skipped "to save time" costs more time later** —
  a KB scaffolded with guessed domains/sensitivity rules gets restructured
  within the first week once the real shape becomes obvious. The five
  minutes of Step 0/0.5 questions is cheaper than a mid-project re-scaffold.
- **A KB with no named success criterion is unroadmappable** — "organize my
  stuff" produces a tidy tree nobody opens again. If Step 0.5's answer stays
  vague after one follow-up, propose a concrete default success criterion
  yourself and get a yes/no rather than scaffolding against nothing.
- **Don't build automation infrastructure (routines/, cache files) if Step 0
  said manual-only** — empty scaffolding for a feature nobody asked for is
  clutter, not preparedness.

## See Also

- `kb-health-audit` — the periodic maintenance/audit counterpart; run it
  immediately after genesis (Step 8) and then on the cadence the user
  chooses going forward.
- `facts-registry-propagation` — the exact update chain to run whenever a
  figure already tracked in `facts.yml` changes; reference it from the
  governing file written in Step 2 instead of re-deriving the chain there.
