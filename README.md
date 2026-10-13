# Agent Ops Skills

Battle-tested [Claude Skills](https://docs.claude.com/en/docs/claude-code/skills) /
agent-runtime skills for running **multi-agent AI operations** — not single-shot
prompts. Each one was distilled from a real incident (a cost spike, a botched
merge, a silently fabricated dashboard) and turned into a procedure with
runnable scripts, not just prose.

Framework-agnostic: works with [Hermes](https://github.com/NousResearch/hermes),
Claude Code, LangChain/LangGraph, CrewAI, AutoGen, or a bare OpenAI-compatible
API — see each skill's `references/framework-adapters.md`.

## What's here

| Skill | Problem it solves |
|---|---|
| [`tiered-model-delegation`](skills/tiered-model-delegation/) | You're burning frontier-model tokens on mechanical execution. Plan once with a strong model, execute with a cheap one — safely, with the guardrails that stop a cheap model from silently guessing on unresolved decisions. |
| [`merge-reconciler`](skills/merge-reconciler/) | Two AI agents produced conflicting branches and neither should resolve its own conflict (they're structurally biased toward their own diff). A neutral third-party procedure + script to classify and resolve every hunk. |
| [`task-scoped-watchdog`](skills/task-scoped-watchdog/) | A monitoring cron for one background build/dispatch gets left running forever, burning cycles on checks with nothing to watch. A lifecycle gate (script + scheduler adapters) that scopes the watchdog's active window to the target's actual lifetime, with a TTL so a forgotten deactivation self-expires. |
| [`kb-genesis`](skills/kb-genesis/) | Standing up a new agentic knowledge-base filesystem gets freelanced from scratch every time, with the same structural mistakes recurring (guessed domains, skipped permission tables, no facts registry, no named success criterion). A batched onboarding interview — now including goal-clarifying questions borrowed from app-build discovery (the one-sentence job, 90-day success criteria, rollout horizon) — plus a proven scaffold (sources/wiki/projects/facts-registry/permission-table) and a generated `ROADMAP.md`, taking a KB from nothing to fully active and trackable. |
| [`kb-health-audit`](skills/kb-health-audit/) | Governing files (system prompts, CLAUDE.md) and automations silently drift from reality — a profile claimed "retired" with its gateway still running, a cron job described in docs that was never actually created. A scheduled (monthly/biweekly) two-part audit: mechanical KB filesystem health (broken links, fact drift) plus a prompt audit that verifies claims against the live filesystem/process state instead of trusting the docs. |
| [`facts-registry-propagation`](skills/facts-registry-propagation/) | A KB's facts registry gets built at genesis, then nobody updates it correctly when a tracked figure actually changes — leading to superseded numbers sitting live on wiki pages for months with no mechanism to catch it. The exact 7-step propagation chain (update registry → retire old value with a tight allowlist → grep-propagate to every quoting page → append to metric history → sync every dashboard surface in one pass → update topic memory → re-run the health check) so the registry stays a source of truth instead of becoming just another stale copy of the number. |

## Why these six

Most "agent skill" repos are wrappers around a library's own docs (turn
python-pptx into a skill, turn `gh` into a skill). These aren't that — they
encode judgment calls that cost real money or real bugs to learn:

- **Tiered delegation**: the failure mode isn't "how do I call two models,"
  it's *the cheap model will confidently guess on anything left ambiguous,
  and the wrong guess ships as working code.* The skill is built around
  closing every ambiguity before dispatch, and a two-gate review (audit the
  plan before it runs, audit the output before you trust the summary).
- **Merge reconciliation**: agents resolving conflicts against a peer's work
  reliably either overwrite the peer or abandon their own change — they lack
  the peer's context and are biased toward their own side. This is the
  neutral-arbiter pattern that fixes it, plus a script that extracts and
  classifies every conflicted hunk instead of eyeballing diff markers.
- **Task-scoped watchdog**: the failure mode isn't "how do I poll a
  background task," it's that polling defaults to always-on and keeps
  running after the thing it watches is done. The skill is a lifecycle gate
  — activate at dispatch, deactivate on resolution, TTL as a self-expiring
  safety net — plus the exact pause/resume call for five different
  scheduler primitives.
- **KB genesis**: the failure mode isn't "how do I make folders," it's that
  every from-scratch build guesses at domains, sensitivity rules, and
  automation needs instead of asking — producing a structure that gets
  re-scaffolded within a week once the real shape becomes obvious, or a tidy
  tree nobody ever opens again because no one named what it was actually
  *for*. The skill is a mandatory batched onboarding interview before any
  file gets created — now paired with goal-clarifying questions (the
  one-sentence job, 90-day success criteria) borrowed from `appbuild`'s
  Discovery phase — plus a scaffold proven end-to-end (facts registry,
  dependency graph, permission table) and a generated `ROADMAP.md` so the
  build is trackable against its own stated goal, instead of ad hoc folders
  with no way to tell if they're "done."
- **KB health audit**: the failure mode isn't "how do I check for broken
  links," it's that an agent's own governing files (system prompt, cron
  job descriptions) silently drift from what's actually running — a
  profile described as "retired" with its gateway process still live, an
  automation documented as "scheduled" that was never actually created as
  a cron job. The skill pairs mechanical filesystem checks with a prompt
  audit that verifies every "done"/"retired"/"live" claim against the real
  process/filesystem state, not the docs describing it.
- **Facts registry propagation**: the failure mode isn't "how do I store a
  number," it's that a registry built to prevent drift gets forgotten the
  moment the real figure actually changes — the registry becomes one more
  place the stale number lives, trusted by default because it *looks* like
  a source of truth. The skill is the exact 7-step chain (retire-with-
  allowlist, grep-propagate, sync every dashboard surface in the same pass,
  re-verify) distilled from an incident where two live pages kept quoting a
  superseded figure for months because this chain didn't exist yet.

## Install

Drop a skill directory under wherever your agent runtime loads skills from
(for Claude Code / Hermes: `~/.hermes/skills/<category>/<name>/` or a
project's `.claude/skills/`). Each `SKILL.md` is self-contained; the
`scripts/` and `references/` subfolders are loaded on demand.

## License

MIT — see [LICENSE](LICENSE).
