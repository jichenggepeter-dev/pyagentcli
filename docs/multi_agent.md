# Multi-Agent v0.3

PyAgentCLI now has explicit role contracts for the planned execution path:

```text
Planner Agent
  -> PlanPreview / PlanStep
Executor Agent
  -> ExecutorStepContract
Reviewer Agent
  -> ReviewReport / ReviewerGateDecision
```

Each planned run can also persist role handoffs:

```text
Planner handoff
  -> Executor handoff(s)
  -> Reviewer handoff
```

Handoffs are saved inside the plan JSON and shown by `--show-plan`, so a user can inspect how the work moved between roles.

## Role Configuration

Planner, Executor, and Reviewer can have separate role configuration in `pyagent.toml`:

```toml
[agents.planner]
model = "gpt-4.1-mini"
system_prompt = "Plan with small, safe, reviewable steps."

[agents.executor]
model = "gpt-4.1-mini"
system_prompt = "Execute exactly the approved step and stop."

[agents.reviewer]
model = "gpt-4.1-mini"
system_prompt = "Review conservatively and recommend the next action."
```

Current behavior:

- Planner uses the planner model and planner system prompt.
- Planned execution uses the executor model and executor system prompt.
- Reviewer config is parsed and reserved for model-backed review and retry proposal generation; the current Reviewer gate remains deterministic.
- If a role does not define a model, PyAgentCLI uses the default `PYAGENT_MODEL`.

## Planner

The Planner produces a structured `PlanPreview`:

- summary
- ordered steps
- suggested tools
- risk level per step

The Planner does not call tools or edit files.

After producing a plan, PyAgentCLI records a planner handoff with:

- role
- summary
- status
- risk summary
- next action

## Executor

The Executor receives one `ExecutorStepContract` per approved plan step.

The contract includes:

- original user goal
- step id
- title
- risk
- suggested tools
- instructions

The executor prompt marks the role explicitly:

```text
Role: Executor Agent
```

The Executor stops after the step and summarizes what happened.

During plan execution, PyAgentCLI records executor handoffs for:

- plan execution start
- completed steps
- skipped approval-denied steps
- failed steps
- final execution completion

## Reviewer Gate

The Reviewer produces a `ReviewReport` and a `ReviewerGateDecision`.

The gate is intentionally conservative:

- `success` steps pass
- `failed`, `skipped`, or `cancelled` steps block automatic success

WRITE and EXECUTE risks do not block by themselves. They produce risk notes and suggested tests.

If a plan run was marked `success` by execution but the Reviewer gate blocks, PyAgentCLI changes the final plan status to `failed` and persists the review result.

The Reviewer also writes a handoff recommendation, such as:

- accept after running suggested verification commands
- retry the failed step after inspecting the execution result
- ask the user to retry, explicitly skip, or accept skipped work as out of scope

Reviewer recommendations do not automatically retry or execute tools. The user still decides whether to resume, retry, skip, or accept.

## Retry Proposal

When the Reviewer gate blocks, PyAgentCLI can include a read-only retry proposal:

```text
Retry proposal:
- Recommended action: retry_step
- Target step: S2
- Reason: The step failed during execution.
- Suggested command: `pyagent --retry-step PLAN_ID S2`
- Requires approval: yes
```

Proposal behavior:

- `failed` step -> propose `retry_step`
- `skipped` step -> propose a user decision with an optional retry command
- `cancelled` step -> propose `resume_plan`
- `success` plan -> no retry proposal

The proposal is only text stored in the review and plan output. It does not execute tools or retry automatically.

## Why This Matters

This prevents a common agent failure mode:

```text
Step S1 succeeded
Step S2 was skipped
Plan status says success
```

With the Reviewer gate, skipped or failed work cannot silently become a successful plan.

With persisted handoffs, the plan also answers:

```text
Who produced the plan?
What did the executor complete or skip?
What did the reviewer recommend next?
```

## Next Steps

- Add model-backed Reviewer proposal generation using the existing reviewer role config.
- Compare deterministic Reviewer proposals against model-backed suggestions in evals.
- Compare deterministic retry proposals against model-backed proposals in evals.
