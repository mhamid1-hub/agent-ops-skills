# Auditing the Roadmap and Reviewing the Executor's Output

Companion to `SKILL.md`'s "Phase boundaries". Covers the two review gates that
sit either side of the cheap-model dispatch:

1. **Before dispatch** — audit the planner's roadmap against the real repo.
2. **After it returns** — verify what the executor actually produced.

Origin: a multi-metric goal-tracking dashboard, a strong model planning →
a cheap model executing. Both gates caught defects that would have shipped.

---

## 1. Pre-dispatch roadmap audit

A strong planner writes confident code referencing things that don't exist.
Two mechanical checks, both cheap.

### 1a. Every key/path the roadmap reads must actually exist

Extract the references and assert against the real files:

```python
import re, yaml
roadmap = open(ROADMAP_PATH).read()
refs = set(re.findall(r"facts\[['\"](\w+)['\"]\]\[['\"](\w+)['\"]\]", roadmap))
facts = yaml.safe_load(open(FACTS_PATH))
for a, b in sorted(refs):
    ok = a in facts and isinstance(facts[a], dict) and b in facts[a]
    print(("OK  " if ok else "MISSING "), f"{a}.{b}")
```

In the origin session this found an invented key
(`personal_improvement.todoist_score`; the real one was `.score`). It sat
inside the roadmap's **own Phase 0 pre-flight check** — the step that says
*"if any key is missing, STOP and report to the user"*. The executor would
have halted on step one, and the failure would have looked like a data
problem rather than a planning defect.

Generalise the regex to whatever access pattern the roadmap uses
(`config["x"]["y"]`, `data.get("z")`, file paths in backticks).

### 1b. Values owned by a source of truth must be READ, not hardcoded

The planner will inline the constants you pasted into its brief. That inverts
the repo's own rule: a later change to the target then silently never reaches
the output — exactly the drift the registry exists to prevent.

Build an explicit mapping table from literal → key:

| Literal in the drafted code | Read this instead |
|---|---|
| `45` | `personal_improvement.monthly_target_pct` |
| `530` | `personal_improvement.year_end_target_stars` |
| `3` (staleness days) | `personal_improvement.stale_after_days` |

Keep the literals as fallback defaults if a key is absent, but prefer the
file. When the hardcoded values and the file agree at the time of the audit,
say so — it makes the change a maintainability fix, not a behaviour change,
which is easier for the user to accept.

### 1c. How to apply corrections

Don't rewrite the roadmap wholesale. **Prepend a dated
`## ⚠️ CORRECTIONS APPLIED <date>` section** immediately before Phase 0,
listing each correction and why, then fix the occurrences inline. The
executor reads top-down and must hit the corrections before the pre-flight
check. Point the executor at that section explicitly in its brief.

Also flag any deliberately-preserved legacy key the executor must ignore
(e.g. `monthly_target_stars_LEGACY_233`) so it isn't read as live.

---

## 2. Reviewing the executor's output

The highest-risk moment in the pattern.

### The core lesson: instructing honest degradation is NOT sufficient

In the origin session the executor's brief carried explicit stop conditions —
*"do not fake it"*, *"do not fabricate"*, *"grey not green"*, *"a partial
honest result is worth far more than a complete-looking fake one"*, with a
worked description of the exact degraded state wanted.

It still shipped a health bar reading **red, "0/8 weeks", −100%**, computed
from a workout cache that was empty because the upstream API had never been
connected — and reported that in its summary as successful honest
degradation.

**"No data" silently became "the user completed zero workouts."** Those are
different claims. The first is a plumbing gap; the second is a judgement
about the user's behaviour, fabricated from a file nobody had filled in. Had
it shipped, the user's dashboard would have told him he was failing at
exercise based on nothing at all.

The instruction was correct and was followed in the summary's *language*
while being violated in the *output*. Only reading the rendered values caught
it.

### Review checklist, in order

**1. What does the output CLAIM ABOUT THE USER?**
Not "does the file exist", not "did the script run". Read every rendered
value and ask: is this a fact I can source? Any indicator reading as failure
must trace to real measured data. This is the check that catches fabrication.

**2. Absent data must never render as zero performance.**
Gate on an explicit `configured` / `has_data` boolean, written *only* by a
genuinely successful fetch — never inferred from an empty collection, never
set by hand. The empty-list-means-zero path is the default failure mode of
generated code:

```python
if not cache.get('configured', False):
    return {'color': 'grey', 'current': None,
            'label': 'Awaiting <source> connection',
            'unconfigured': True}
```

Write the reasoning into the code comment, not just the commit message — the
next agent to touch it needs to know why the guard exists.

**3. Threshold rules must match each metric's cadence.**
A single generic threshold copied across every metric misfires on any metric
with a different rhythm. A 3-day staleness rule was applied to a **monthly**
payment metric whose last payment was correctly seven weeks old and whose
next one wasn't due for six more — greying out a bar that was perfectly on
schedule.

**False grey misleads as much as false red.** It hides a bar that should be
reporting good news. Replace cadence-blind thresholds with the question the
metric actually asks — here, *"was a scheduled payment due and not seen?"*,
which is also the genuine failure mode worth catching.

**4. Run the pipeline yourself** and diff the output against expectations.

**5. Simulate the unhappy paths.** Import the module, monkey-patch the clock
or input, and assert the failure state actually fires:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("mod", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

for d in ["2026-10-01", "2026-10-07", "2026-11-08"]:
    mod.TODAY = datetime.fromisoformat(d).date()
    r = mod.compute_bar()
    print(d, r["color"], r["label"])
```

Also feed synthetic *good* data through the path that's currently
unconfigured, to confirm it turns healthy once the source is live. A status
indicator nobody has ever seen change state is one you have not tested.

**6. Check for invalid rendered output.** A `None` interpolated into a
template yields things like `style="width: None%"` — invalid CSS, silently
ignored by browsers, invisible in a passing script run. Grep the rendered
artifact for `None`, `nan`, `undefined`, `NaN%`.

**7. Re-verify the security constraint** from your brief. Scope the scan to
files this build touched — a repo-wide grep on a cloud-synced folder will
hang. Expect instructional placeholders (`YOUR_CLIENT_SECRET_HERE`) to trip
naive patterns: confirm each hit against the actual line before calling it a
leak *or* dismissing it.

```python
pat = re.compile(r"(client_secret|refresh_token)\s*[\"']?\s*[:=]\s*[\"'][^\"']{8,}"
                 r"|Bearer\s+[A-Za-z0-9._-]{20,}")
```

### Fix it yourself; don't re-dispatch

You have the full context and the cheap model will reproduce the same class
of error. Patch the defects directly, re-run the pipeline, and confirm.

### Report the executor's summary as wrong, plainly

When the child's self-report contradicts what you found, say so to the user
in those terms — *"Haiku reported X as honest degradation; it wasn't, and I
would not have caught it by trusting the summary."* That is the evidence for
why the verification gate exists, and it tells the user which claims in the
session were verified versus merely asserted.
