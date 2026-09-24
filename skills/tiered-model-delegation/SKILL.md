---
name: tiered-model-delegation
description: "Strong model plans, cheap model executes — safely, with cost proof."
version: 2.0.0
author: mhamid1-hub
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [delegation, subagents, model-selection, cost-optimization, roadmap, handoff, orchestration, multi-agent]
  related_skills: [merge-reconciler]
---

# Tiered Model Delegation

Use when you want **different models for different phases** of one job:

> "make a strong model do the roadmap and a cheap model execute it"
> "have the smart model plan it, cheap model can do the grunt work"
> "don't build it yourself — delegate the execution"

The shape is always the same: a **capable model writes a specification**, then
a **cheaper model executes it**. The value is cost. The risk is that the cheap
model hits an ambiguity it can't resolve and silently guesses — and the wrong
guess ships as working code, because it *looks* like working code.

This skill is not "how to call two models." It's the three failure classes
that make that pattern unsafe if you skip them, plus runnable scripts so you
don't have to hand-roll the plumbing or the audit every time.

## The three failure classes this guards against

1. **Unresolved ambiguity ships as a guess.** If your own analysis ended on
   an open question, a cheap executor will pick something plausible and
   proceed. → §1 Resolve before dispatch.
2. **The plan references things that don't exist, or hardcodes values that
   should be read from a source of truth.** A confident planner writes
   confident code against invented keys/paths. → §3 Pre-dispatch audit.
3. **"Honest degradation" instructions get followed in language, violated in
   output.** An executor can produce a fabricated-looking result while its
   own summary claims correct degraded behavior. → §4 Output review.

## 0. Check what your runtime actually supports

**Per-task model pinning is not always available.** Some orchestrators
(Hermes `delegate_task`, for one) only support a *global* model pin —
children inherit the parent's model unless the runtime config is changed
between phases. Others (raw API calls, LangGraph, CrewAI with per-agent LLMs)
let you pin per-call. Check first:

```bash
hermes config get delegation      # Hermes: model, provider, max_concurrent_children
```

If it's global-only, switching models mid-job means editing global state.
Treat that like any other prod config change:

```bash
cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak-<job>-$(date +%Y%m%d)
hermes config set delegation.model <planner-model>
hermes config set delegation.provider <planner-provider>
hermes config get delegation | head -3       # verify it landed
# ... dispatch planner ...
hermes config set delegation.model <original-default>   # restore before executor runs on the wrong tier
```

If your runtime supports per-call model selection (raw API, LangChain,
CrewAI, AutoGen), skip the config dance entirely — see
`references/framework-adapters.md` for the exact call shape in each.

## 1. Resolve every open decision BEFORE dispatching the planner

The single highest-value step, and the most often skipped. A cheap executor
**cannot** resolve a judgement call. If your analysis ended on blocking
questions, those get answered before the *planner* runs, not before the
executor runs — otherwise the planner bakes its own guess into the spec and
the executor inherits it with false confidence.

Order that works:

```
open questions → decide (ask the user, or apply a documented default)
              → write decisions into the source of truth (config/data file)
              → verify they parse/read back correctly
              → dispatch planner → audit roadmap → dispatch executor → review output
```

If you must keep moving with items open, mark them `TODO(decide)` in the
planner's brief explicitly and tell the executor's brief it must **stop and
report**, not guess, on anything still marked that way.

## 2. Writing the planner's brief

State the quality bar directly, as the primary instruction:

> The plan must be executable by a less capable model with no further
> clarification. Every step needs exact file paths, exact function
> signatures, exact data shapes, exact formulas, and explicit "done when"
> criteria. Anywhere a judgement call exists, make the decision in the plan
> — do not leave it open.

Include in the brief:

- **All decided values verbatim**, marked `do not re-derive or change these`.
- **Architecture decisions already made**, marked `do not revisit`.
- **Verified external facts** (API versions, rate limits, what an API
  notably does *not* expose) so neither model re-researches and neither
  builds against a dead spec.
- **Repo conventions**: date formats, source-of-truth location, existing
  check scripts that must keep passing. Point at project-local docs by path.
- **Security constraints, explicitly**: where secrets must live and where
  they must never land (synced folders, the repo, a wiki page).
- **Scope fences**: what's out of scope this pass.
- Tell the planner to write **only** the plan — no implementation code, no
  edits to existing files. A planner that starts building defeats the split.

## 3. Pre-dispatch roadmap audit (before the executor ever runs)

Two mechanical, cheap checks — run `scripts/audit_roadmap.py`:

```bash
python3 scripts/audit_roadmap.py --roadmap plan.md --repo . \
    --data-file facts.yml --literals "45=personal.monthly_target_pct,530=personal.year_target"
```

It flags:
- **References to keys/paths that don't exist** in the named data file or
  repo — a planner will confidently write `facts["x"]["y"]` for a key that
  was never there. Caught early, this is a one-line fix; caught by the
  executor it looks like a data problem and the executor may halt or (worse)
  work around it silently.
- **Hardcoded values that should be reads** — the planner inlines the
  constants you pasted into its brief, which inverts your source-of-truth
  rule: a later change to the real value then never reaches the output.

Apply corrections by **prepending** a dated `## ⚠️ CORRECTIONS APPLIED`
section right before the plan's first executable step — don't silently
rewrite; the executor should see what was wrong and why.

## 4. Phase boundaries and dispatch

Dispatch is asynchronous — don't poll. Use the gap to apply user decisions to
the repo and run existing checks.

1. Planner result returns → **read the plan yourself** before flipping
   models. A vague plan produces a wrong build; cheaper to catch now.
2. Flip to the cheap model (see §0), verify.
3. Dispatch the executor with the plan path and the same scope fence.
4. **Verify the executor's work independently — see §5.** A child's summary
   is a self-report, not a fact.
5. Restore the model pin if global.

## 5. Reviewing the executor's output — the highest-risk gate

**Instructing honest degradation is not sufficient.** A real incident: an
executor's brief explicitly said "do not fake it, grey not green, a partial
honest result beats a complete-looking fake one" — and it still shipped a
health indicator reading red / "0/8 weeks" / −100%, computed from an empty
cache because the upstream source was never connected, and reported this in
its summary as *successful honest degradation*. "No data" silently became "the
user failed at the thing." Only reading the rendered values caught it.

Run `scripts/review_output.py` for the mechanical half of this gate:

```bash
python3 scripts/review_output.py --artifact dashboard.html --module compute.py \
    --unhappy-dates 2026-10-01,2026-10-07,2026-11-08
```

It checks:
1. **Rendered claims, not process success.** Greps the artifact for
   `None`, `nan`, `undefined`, `NaN%` — invalid values a template silently
   swallows into broken-but-passing output.
2. **Absent-data-as-zero-performance.** Confirms any "empty" state is gated
   by an explicit `configured`/`has_data` flag set only by a real successful
   fetch — never inferred from an empty collection.
3. **Cadence-blind thresholds.** A single staleness rule applied to metrics
   with different natural rhythms misfires — e.g. a 3-day rule flagging a
   monthly metric that's correctly 7 weeks into a stable cycle. Ask what the
   metric is actually testing, not a generic "how old is this."
4. **Unhappy-path simulation.** Imports the module, monkey-patches the given
   dates/inputs, and prints what state fires — a status indicator nobody has
   ever seen change state hasn't been tested.
5. **Secret-scan on touched files only** (not a repo-wide sync-folder grep
   that hangs), with a check against instructional placeholders so
   `YOUR_CLIENT_SECRET_HERE` doesn't false-positive.

Then read every rendered value yourself and ask: **is this a fact I can
source, or a plausible-looking number nobody actually measured?** That
judgment call is the part no script does for you.

Fix defects yourself — you have full context and the cheap model will
reproduce the same class of error on a retry. When the executor's summary
contradicted what you found, say so to the user in those terms: *"the
executor reported X as honest degradation; it wasn't."* That's the evidence
for why the gate exists.

## Cost accounting — prove the savings, don't assert them

Every use of this pattern should end with an actual number, not a vibe. Use
`scripts/cost_estimator.py` to turn token counts (planner + executor +
review-fix tokens) into a real dollar comparison against single-tier cost:

```bash
python3 scripts/cost_estimator.py \
    --planner-model claude-opus-4 --planner-tokens 8000 \
    --executor-model claude-haiku-4 --executor-tokens 40000 \
    --single-tier-model claude-opus-4
```
Prints planner cost, executor cost, total, and what the same 48K tokens would
have cost run entirely on the planner-tier model. If the split doesn't
actually save money for a given job size (small jobs, or a planner brief that
ends up longer than the execution it specs), say so — don't tier by reflex.

## Pitfalls

- Assuming per-task model pinning exists — check first, plan around global-only.
- Leaving a global model pin set after the job — every later delegation
  silently inherits it.
- Dispatching with decisions still open — the executor guesses and the guess ships.
- Letting the planner re-derive settled numbers instead of reading them.
- Trusting the child's summary instead of reading the rendered output.
- Tiering reflexively on jobs too small for the planner-brief overhead to pay
  for itself — run the cost estimator before committing to the split.

## Support files

- `scripts/audit_roadmap.py` — pre-dispatch plan/data-reference audit.
- `scripts/review_output.py` — post-dispatch fabrication/degradation checks.
- `scripts/cost_estimator.py` — token-cost comparison, tiered vs single-model.
- `references/config-and-data-edit-safety.md` — duplicate-key hazards,
  parse-back verification, hand-rolled-validator false positives.
- `references/executor-output-review.md` — the full narrative behind §5,
  with worked code for each check.
- `references/framework-adapters.md` — the exact two-phase call shape for
  Hermes, raw OpenAI-compatible API, LangChain/LangGraph, CrewAI, and AutoGen.
