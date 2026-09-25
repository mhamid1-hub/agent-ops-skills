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

## Why these three

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

## Install

Drop a skill directory under wherever your agent runtime loads skills from
(for Claude Code / Hermes: `~/.hermes/skills/<category>/<name>/` or a
project's `.claude/skills/`). Each `SKILL.md` is self-contained; the
`scripts/` and `references/` subfolders are loaded on demand.

## License

MIT — see [LICENSE](LICENSE).
