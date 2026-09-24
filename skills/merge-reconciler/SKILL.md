---
name: merge-reconciler
description: "Neutral third-party resolution of AI agent merge conflicts."
version: 2.0.0
author: mhamid1-hub
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [multi-agent, git, merge-conflict, arbitration, orchestration]
  related_skills: [tiered-model-delegation]
---

# Merge Reconciler

Resolve a git merge conflict between two AGENTS' branches as an impartial
third party. Agents resolving conflicts against a peer's work reliably either
overwrite the peer or abandon their own change — they lack the peer's context
and are structurally biased toward their own side, the same way a person
editing their own PR against a reviewer's conflicting suggestion tends to
keep their own line. This skill is the fix: a neutral reconciler that
receives both diffs plus both sides' stated intents and produces a merged
result, like a merge-queue arbiter for AI-generated branches.

## When to use

- Two agent branches/worktrees collide during a parallel multi-agent run
  (task-queue engineering pipeline, parallel-PR wave, multi-worktree refactor).
- `git merge` or `git rebase` halts on conflicts between two agents' work and
  neither original agent should self-adjudicate.
- Do **not** use for conflicts within a single agent's own work, or for
  trivial lockfile/generated-file conflicts (regenerate those instead).

## Prerequisites

- A repo checkout containing the halted merge, or the two branch names plus
  permission to run the merge yourself.
- Both sides' stated intent: task-tracker completion notes, PR bodies, or at
  minimum each branch's commit messages.
- The project's build/test command, if one exists.

## How to run

**Standalone**: a human or agent invokes this skill inside the conflicted
repo and follows the procedure below.

**Spawned neutral agent** (preferred in multi-agent pipelines): dispatch a
fresh subagent whose task contains the repo path, both branch names, and
both sides' intent summaries verbatim, with an instruction to follow this
skill. The reconciler must NOT be one of the two agents that produced a
conflicting side — see the impartiality contract below.

## Quick reference

| Hunk class | Definition | Resolution |
|---|---|---|
| disjoint-intent | The two changes serve different goals and can coexist | Combine both |
| same-question-different-answer | Both sides answered one design question differently | Pick ONE per stated intents; surface the decision |
| superseded | One side's premise no longer holds after the other's change | Keep the surviving side; note why |

Impartiality contract: never favor the side that spawned you; touch ONLY
conflicted regions (no drive-by edits); every design-question pick must
appear explicitly in the hand-back summary.

## 1. Gather both sides

Run via terminal:

```bash
git status                              # confirm conflicted state, list conflicted files
git merge-base <branch-A> <branch-B>
git log --oneline <base>..<branch-A>
git log --oneline <base>..<branch-B>
git diff <base>..<branch-A> -- <file>   # per conflicted file, both sides
git diff <base>..<branch-B> -- <file>
```

In a halted merge, `HEAD` is one side and `MERGE_HEAD` is the other.

Collect each side's intent from whatever tracker/PR system produced the
branches (completion notes, PR body, commit messages). Write down **one
sentence of intent per side** before touching any file — this is what every
same-question-different-answer decision gets checked against later.

Done when: you can state both intents in your own words and have both diffs
for every conflicted file.

## 2. Classify every conflicted hunk

Run `scripts/classify_conflicts.py` to extract every `<<<<<<<`/`=======`/
`>>>>>>>` block across the repo mechanically — this is the step people do by
eyeballing diffs and miss hunks in large files:

```bash
python3 scripts/classify_conflicts.py --repo /path/to/repo
```

It prints, per file, every conflict marker block with line numbers and both
sides' content side by side, plus a suggested class based on heuristics
(identical-except-whitespace → likely same-question; non-overlapping line
ranges touched by the same rebase → likely disjoint) that you confirm or
override — it does not decide for you, it removes the "did I even see every
hunk" risk.

For each printed hunk, assign exactly one class from the Quick Reference
table, judging by the **stated intents**, not which change looks nicer. If a
single hunk contains multiple independent decisions (new logic that combines
cleanly PLUS a styling/rounding choice both sides answered differently),
decompose it into sub-decisions and classify each one.

Done when: every hunk has a written class and a one-line rationale.

## 3. Resolve under the impartiality contract

Edit each hunk with a patch tool or direct file edit:

- **disjoint-intent** → merge both changes so each intent is fully served.
- **same-question-different-answer** → pick the answer that best serves the
  STATED intents (e.g. an intent of "strict validation" beats "quick default"
  if the task required correctness). Never split the difference into a
  hybrid neither side asked for — that produces code nobody designed and
  nobody will recognize in review.
- **superseded** → keep the surviving side; delete the dead premise.

Never favor the side that spawned you. If intents genuinely tie, escalate
rather than guess — see §5.

Change nothing outside conflict markers — no formatting, renames, or
opportunistic fixes; that makes the merge unreviewable.

`git add` each resolved file.

Done when: `scripts/classify_conflicts.py --repo . --check` exits 0 (no
remaining conflict markers) and every resolved file is staged.

## 4. Verify

Run the project's build/tests. At minimum, import/execute the touched
modules. Both intents must be **observably present in the merged behavior**
(side A's new semantics AND side B's disjoint addition both present) — not
just present in the merged text.

Complete the merge: `git commit` (default merge message plus a body listing
hunk decisions is fine — that body is your audit trail).

Done when: verification passes and the merge commit exists.

## 5. Hand back

Produce a completion summary naming **every** hunk decision:

```
file:lines — class — which side(s) kept — rationale
```

For every same-question-different-answer hunk, state the design question and
the answer you picked so a human can veto it — never bury a design call
inside a generic "resolved conflicts" message.

If intents tied and you escalated instead of guessing, say exactly which
hunk and why neither side's intent clearly wins — this is not a failure of
the reconciliation, it's the correct output when there genuinely isn't
enough information to arbitrate.

## Pitfalls

- **Self-favoring**: if you were spawned by one of the conflicting agents,
  you are structurally biased — state this explicitly and weigh the other
  side's intent deliberately. Prefer the third-profile/fresh-subagent shape
  so this never arises in the first place.
- **Splitting the difference** on a design collision produces a hybrid
  nobody designed; pick one answer and surface it.
- **Per-file classification** instead of per-hunk: files usually mix hunk
  classes; classifying a whole file as one class silently drops a disjoint
  change buried next to a superseded one.
- **Drive-by edits** make the merge unreviewable and steal decisions from
  the original agents.
- **Missing intents**: commit messages alone are often thin; prefer
  task-tracker completion notes or PR bodies. If neither side's intent is
  recoverable, escalate instead of guessing.
- **Repeat offenders**: the same file conflicting across multiple rounds is
  a hotspot signal, not routine reconciliation work — flag it (e.g. a
  `hotspot: <path> — <reason>` note back to whoever's coordinating the
  agents) so that file gets decomposed into smaller independent units,
  rather than serially reconciling every new collision on it forever.

## Verification checklist

- `git status` shows a clean tree on the target branch with a merge commit.
- `scripts/classify_conflicts.py --repo . --check` finds no conflict markers.
- Build/tests pass; both sides' intents are demonstrably present, or the
  dropped one is explicitly named in the hand-back summary.
- The hand-back summary enumerates every hunk with class and rationale.

## Support files

- `scripts/classify_conflicts.py` — extracts every conflict-marker block in
  a repo with line numbers and both sides' content, suggests a class per
  heuristics, and (`--check`) verifies zero markers remain post-resolution.
- `references/multi-agent-adapters.md` — how to invoke this as a neutral
  reconciler under Hermes kanban, a GitHub Actions merge-queue bot, a plain
  git-worktree parallel-agent setup, or CrewAI/AutoGen crews writing to
  shared branches.
