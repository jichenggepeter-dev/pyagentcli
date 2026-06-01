# Multi-Agent v0.2

PyAgentCLI now has explicit role contracts for the planned execution path:

```text
Planner Agent
  -> PlanPreview / PlanStep
Executor Agent
  -> ExecutorStepContract
Reviewer Agent
  -> ReviewReport / ReviewerGateDecision
```

## Planner

The Planner produces a structured `PlanPreview`:

- summary
- ordered steps
- suggested tools
- risk level per step

The Planner does not call tools or edit files.

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

## Reviewer Gate

The Reviewer produces a `ReviewReport` and a `ReviewerGateDecision`.

The gate is intentionally conservative:

- `success` steps pass
- `failed`, `skipped`, or `cancelled` steps block automatic success

WRITE and EXECUTE risks do not block by themselves. They produce risk notes and suggested tests.

If a plan run was marked `success` by execution but the Reviewer gate blocks, PyAgentCLI changes the final plan status to `failed` and persists the review result.

## Why This Matters

This prevents a common agent failure mode:

```text
Step S1 succeeded
Step S2 was skipped
Plan status says success
```

With the Reviewer gate, skipped or failed work cannot silently become a successful plan.

## Next Steps

- Split Planner, Executor, and Reviewer into model-backed role clients.
- Add Reviewer suggestions that can trigger automatic retry.
- Feed Reviewer gate outcomes into eval scoring.
