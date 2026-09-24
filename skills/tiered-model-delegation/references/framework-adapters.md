# Framework Adapters

The plan/audit/execute/review cycle in `SKILL.md` is framework-agnostic. Here
is the exact call shape per runtime, so you don't have to reverse-engineer it.

## Hermes (`delegate_task`)

No per-task model param — pin globally, dispatch, restore:

```bash
hermes config set delegation.model claude-opus-4 && hermes config set delegation.provider anthropic
# dispatch planner via delegate_task, wait for result, audit it
hermes config set delegation.model claude-haiku-4
# dispatch executor via delegate_task with the audited plan path
hermes config set delegation.model <original>   # restore
```

## Raw OpenAI-compatible API (any provider)

Per-call model selection — no global state, no restore step:

```python
from openai import OpenAI
client = OpenAI()

plan = client.chat.completions.create(
    model="gpt-5",
    messages=[{"role": "user", "content": planner_brief}],
).choices[0].message.content

# audit_roadmap.py here

result = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": f"Execute this plan exactly:\n\n{plan}"}],
).choices[0].message.content

# review_output.py here
```

## LangChain / LangGraph

Bind different models to different nodes in the same graph:

```python
from langchain_anthropic import ChatAnthropic

planner = ChatAnthropic(model="claude-opus-4")
executor = ChatAnthropic(model="claude-haiku-4")

def plan_node(state):
    return {"plan": planner.invoke(planner_brief(state)).content}

def audit_node(state):
    # shell out to audit_roadmap.py, or reimplement its checks inline
    ...

def execute_node(state):
    return {"result": executor.invoke(f"Execute exactly:\n{state['plan']}").content}

def review_node(state):
    # shell out to review_output.py
    ...

graph.add_node("plan", plan_node)
graph.add_node("audit", audit_node)
graph.add_node("execute", execute_node)
graph.add_node("review", review_node)
graph.add_edge("plan", "audit")
graph.add_edge("audit", "execute")
graph.add_edge("execute", "review")
```

The audit/review nodes are the part people skip when wiring this up fast —
don't; they're what this skill is actually for.

## CrewAI

Per-agent `llm=` param, same crew:

```python
from crewai import Agent, Task, Crew

planner = Agent(role="Planner", llm="claude-opus-4", goal="Write an executable plan")
executor = Agent(role="Executor", llm="claude-haiku-4", goal="Execute the plan exactly, flag ambiguity")

plan_task = Task(description=planner_brief, agent=planner, expected_output="A step-by-step plan")
# run audit_roadmap.py against plan_task.output before building exec_task
exec_task = Task(description="Execute this plan exactly: {plan}", agent=executor, context=[plan_task])

crew = Crew(agents=[planner, executor], tasks=[plan_task, exec_task])
result = crew.kickoff()
# run review_output.py against the artifacts crew produced
```

## AutoGen

Two `AssistantAgent`s with different `llm_config`, chained via
`initiate_chat` or a `GroupChat`:

```python
from autogen import AssistantAgent

planner = AssistantAgent("planner", llm_config={"model": "claude-opus-4"})
executor = AssistantAgent("executor", llm_config={"model": "claude-haiku-4"})

planner_reply = planner.generate_reply(messages=[{"role": "user", "content": planner_brief}])
# audit_roadmap.py against planner_reply here
executor_reply = executor.generate_reply(
    messages=[{"role": "user", "content": f"Execute exactly:\n{planner_reply}"}]
)
# review_output.py against executor_reply / its side effects
```

## The parts that don't change per framework

- §1 (resolve ambiguity before the planner runs) is a *process* step, not a
  framework feature — do it before any of the above code runs.
- `scripts/audit_roadmap.py` and `scripts/review_output.py` are plain Python
  CLIs; shell out to them from any framework's node/task/callback.
- `scripts/cost_estimator.py` only needs token counts, which every framework
  above exposes on its response objects (`.usage`, `response_metadata`, etc).
