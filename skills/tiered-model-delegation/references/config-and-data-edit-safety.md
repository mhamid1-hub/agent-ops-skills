# Verifying Config & Data Edits Actually Landed

Companion to `SKILL.md`'s "Applying decisions to a source of truth". The step
between *user decides* and *dispatch executor* is where a wrong value gets
silently persisted — and then read as authoritative by every downstream phase.

Origin: applying user decisions into a data registry (`facts.yml`) before
dispatching a planner/executor pair for a personal tracking dashboard.

---

## 1. The duplicate-key hazard (silent overwrite)

**YAML and JSON keep the LAST occurrence of a duplicated key. No error, no
warning.** If you add a structured value under a key that already exists
elsewhere in the same mapping, one of them wins and it may not be yours.

Real near-miss: a new `monthly_target_score` dict (per-month targets) was added
near the top of a block that *already* contained `monthly_target_score: 233`
about ten lines below. Both parsed fine. The old scalar won, silently replacing
the new per-month mapping with a stale integer — while every diff looked correct
and every edit reported success.

**Guard, in order:**

1. **Before adding a key, grep the whole file for that key name** — not just the
   region you're editing. Long data files repeat concepts.
2. **After editing, parse the file and print back the exact values you set.**
   The diff proves text changed; only a parse proves the value *reads back*.
3. When superseding an old key, **rename it rather than deleting it** if the
   project's convention is to preserve history — e.g.
   `monthly_target_stars_LEGACY_233:` with a comment saying what replaced it and
   `do not quote as a live target`. This removes the collision and keeps the
   reasoning trail.

```python
import yaml
d = yaml.safe_load(open(path))
for k in ["<every key you just wrote>"]:
    print(k, "->", d["<section>"].get(k))
```

If a value reads back wrong or `None`, you have a collision or an indentation
error. Fix before dispatching anything.

## 2. Follow the project's own propagation order

Data registries usually have a documented update chain. Read it and follow it
exactly rather than editing the value alone — the surrounding steps are what
makes the change auditable.

A common shape (adapt to whatever the repo documents):

1. Update the value in the registry **first** — it is upstream of prose.
2. Add the superseded value to a `retired:`/history block, with the tightest
   possible allowlist of files where the old figure is still legitimately
   historical (revision tables, "was X, now Y" sentences).
3. Propagate to every page/dashboard that quotes it.
4. Append a dated point to any time-series file that tracks this metric.
5. Log the change wherever the project logs changes.

Skipping step 2 is the usual failure: the registry is correct, prose still
carries the old number, and any automated check covering that figure quietly
stops covering it.

**When superseding a target or rule that a human wrote, preserve the original
in a collapsed block with the reason it was replaced.** Deleting it loses the
reasoning trail and looks like the rule was never considered.

## 3. Hand-rolled validation produces false positives — verify before reporting

If a repo's own check script won't run, it is tempting to re-implement its logic
inline. Do it, but **treat any failure it reports as suspect until confirmed
against the source data.**

In the origin session an ad-hoc re-implementation of a "retired figures appear
outside their allowlist" check reported 8 violations in a dashboard file. All 8
were false: each figure *was* explicitly allowlisted, and the bug was in the
path-matching of the throwaway checker (comparing a relative path against
allowlist entries written in a different root form).

**Before reporting a failure you found with your own scratch validator, print
the underlying record** (here: the `allowed_in` list for each flagged pattern)
and confirm the violation is real. Reporting phantom breakage to the user is
worse than not having run the check.

## 4. When a check script produces no output

Some scripts won't emit through a wrapped shell (restrictive permissions,
output redirection being swallowed, guarded commands). Don't conclude the repo
is broken, and don't skip verification.

Do this instead:

- Run **the specific checks that matter for your change** directly, in a few
  lines of Python — the two or three relevant to the files you touched, not the
  whole suite.
- Say plainly in your reply that the script produced no output and that you ran
  the relevant checks manually, so the user knows their tooling needs a look.
- Mention the observable detail you noticed (e.g. unusual file permissions) as
  a lead, without asserting a diagnosis you didn't confirm.

## 5. Verify links and structure on every file you touched

Cheap, and catches the most common markdown-repo breakage — relative links that
look right but don't resolve, especially across sibling directories:

```python
import os, re
for f in touched_files:
    d = os.path.dirname(f)
    for link in re.findall(r'\]\(([^)#][^)]*\.md[^)]*)\)', open(f, errors="ignore").read()):
        if not os.path.exists(os.path.join(d, link.split("#")[0])):
            print("BROKEN:", f, "->", link)
```

## 6. Report the near-miss, don't bury it

If you caught your own mistake mid-task (a duplicate key, a wrong path, a
miscount), say so in the reply with what would have happened had it landed.

It is short, it is honest, and it tells the user which parts of the change were
actually verified versus merely written. Silently fixing your own error and
reporting only success trains the user to trust unverified claims.
