# Reviewer Agent v0.4

Reviewer runs after planned execution.

The core gate is deterministic: it reads the completed `PlanRun`, step risks, execution result, and recent audit logs.

Reviewer v0.2 can also add an optional model-backed suggestion when `[agents.reviewer].model` is configured and an API key is available. That model suggestion is advisory only. It cannot override the deterministic gate and it never executes tools or retries steps.

Reviewer v0.3 adds git diff awareness for local repositories. When the workspace is a git repository, the review artifact includes changed files, added and removed line counts, and bounded hunk headers. Non-git workspaces and clean git repositories are reported clearly instead of failing.

Reviewer v0.4 adds changed-file risk scoring. It scores changed files by path sensitivity, file type, diff size, and deletion-heavy changes, then writes risk level, score, reasons, and suggested tests into the review artifact. This remains advisory and does not change the deterministic gate.

## What It Reports

The review output includes:

- summary of execution status
- risk notes for `WRITE`, `EXECUTE`, `NETWORK`, and `CRITICAL` steps
- failed or skipped step warnings
- suggested tests
- observed tools
- observed paths
- git diff summary when available
- changed-file risk scoring when git diff is available
- optional model-backed reviewer suggestion

The result is written back into the persisted plan as `review_result`, so `--show-plan PLAN_ID` displays it.

PyAgentCLI also writes a Markdown review artifact:

```text
.pyagent/reviews/PLAN_ID.md
```

## Model-Backed Suggestion

The optional model reviewer receives a bounded JSON summary:

- user goal
- plan status
- step statuses and risks
- deterministic gate result
- deterministic retry proposal
- git diff metadata when available
- changed-file risk scoring when available

It must return JSON with:

- summary
- risk notes
- suggested tests
- recommended action
- confidence

Allowed recommended actions are:

- `accept`
- `retry_step`
- `resume_plan`
- `user_decision`
- `inspect`

Invalid or non-JSON model output is downgraded to `inspect` with low confidence.

## Why Deterministic Gate Stays First

For a local coding agent, the first reviewer should be predictable and auditable. This gives the user a stable checklist before introducing a model-based reviewer later.

## Next Steps

1. Add Browser assertion evals for local pages.
2. Add imported-by dependency context.
3. Add richer eval cases for changed-file risk scoring.
