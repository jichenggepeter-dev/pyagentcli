# Reviewer Agent v0.1

Reviewer v0.1 runs after planned execution.

It is deterministic in this version: it reads the completed `PlanRun`, step risks, execution result, and recent audit logs. It does not call an LLM yet.

## What It Reports

The review output includes:

- summary of execution status
- risk notes for `WRITE`, `EXECUTE`, `NETWORK`, and `CRITICAL` steps
- failed or skipped step warnings
- suggested tests
- observed tools
- observed paths

The result is written back into the persisted plan as `review_result`, so `--show-plan PLAN_ID` displays it.

PyAgentCLI also writes a Markdown review artifact:

```text
.pyagent/reviews/PLAN_ID.md
```

## Why Deterministic First

For a local coding agent, the first reviewer should be predictable and auditable. This gives the user a stable checklist before introducing a model-based reviewer later.

## Next Steps

1. Add optional LLM-based review comments.
2. Include git diff summaries when the workspace is a git repository.
3. Feed review results into Eval Harness v0.1.
