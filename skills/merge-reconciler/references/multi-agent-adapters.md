# Multi-Agent Adapters

The neutral-reconciler pattern is framework-agnostic. It needs three inputs
(two branches, two stated intents) and produces one merge commit plus a
decision log. Here's how to wire the dispatch in common setups.

## Hermes (kanban-native)

Create a reconciliation task assigned to a **third profile** (never one of
the two that produced a conflicting side), with BOTH conflicted tasks linked
as parents — the parent links carry both sides' completion summaries into
the reconciler's context automatically:

```python
kanban_create(
    title="reconcile branch-a x branch-b",
    assignee="reconciler",          # NOT the profile that owns branch-a or branch-b
    parents=["task_a_id", "task_b_id"],
    body="Repo: /path/to/repo. Branches: branch-a, branch-b. Follow the "
         "merge-reconciler skill.",
)
```

## Plain git worktrees, no orchestrator

```bash
cd /path/to/repo
git checkout branch-a
git merge branch-b     # halts on conflict
python3 scripts/classify_conflicts.py --repo .
# resolve, then:
python3 scripts/classify_conflicts.py --repo . --check
git commit
```

Have a human or a fresh subagent (never `branch-a`'s or `branch-b`'s own
session — see impartiality contract) run this manually.

## GitHub Actions / merge-queue bot

Trigger on a failed auto-merge / merge-queue conflict event, check out the
conflicted merge into a scratch dir, run `classify_conflicts.py`, and either:

- auto-resolve `disjoint-intent` and `identical-after-normalization` hunks
  (low risk, mechanical), and
- open a draft PR / comment for anything classified
  `same-question-different-answer`, tagging a human — this is the one class
  where an automated bot should not have the final word without stated
  intents to check against.

```yaml
- name: Classify conflicts
  run: python3 scripts/classify_conflicts.py --repo .
- name: Fail if unresolved design questions remain
  run: python3 scripts/classify_conflicts.py --repo . --check
```

## CrewAI / AutoGen crews writing to shared branches

If two crews/agent-teams each push a branch against the same base, spin up a
**separate** crew/agent (not a member of either producing crew) whose sole
task is this skill's procedure, with both crews' task outputs (their
"intent") passed in as context:

```python
reconciler = Agent(role="Merge Reconciler", llm="claude-opus-4",
                    goal="Resolve git conflicts between two agent branches "
                         "impartially, per merge-reconciler skill")
reconcile_task = Task(
    description=f"Repo: {repo_path}. Branch A: {branch_a} (intent: "
                f"{crew_a_output}). Branch B: {branch_b} (intent: "
                f"{crew_b_output}). Resolve every conflict per the "
                f"merge-reconciler skill's classification table.",
    agent=reconciler,
)
```

## What doesn't change

- The impartiality contract (never the same agent/session as either side)
  is a process rule, not a framework feature — enforce it in whichever
  dispatch mechanism you use.
- `scripts/classify_conflicts.py` is a plain Python CLI; run it from any
  CI system or agent framework's shell/tool-call step.
