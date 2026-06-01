# Plan Preview

Plan Preview is the first step toward PaiCLI-style Plan-and-Execute / DAG execution.

Every generated plan is persisted under:

```text
.pyagent/plans/*.json
```

In v0.1, planning is intentionally read-only from the agent runtime perspective:

- It does not call tools.
- It does not edit files.
- It does not run shell commands.
- It returns a human-readable preview of intended steps.

`--execute-plan` adds a first Plan-and-Execute path:

- Generate a plan.
- Warn if the local search index may be stale.
- Ask the user whether to execute it.
- Execute approved plan steps serially.
- Ask before high-risk plan steps.
- Keep tool-level approval for writes and shell commands.

## Usage

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --plan "Read README.md and change Project status from TODO to READY"
```

The output includes a `Plan id`. Use it to inspect the stored plan:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --show-plan PLAN_ID
```

List all stored plans:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --list-plans
```

Resume a `planned` or `failed` plan:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --resume-plan PLAN_ID
```

Resume is step-aware: steps already marked `success` are skipped, and execution continues from `pending`, `failed`, or `running` steps. The execution summary records skipped steps so the user can see what was reused.

Retry a specific step and all following steps:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --retry-step PLAN_ID S2
```

`--retry-step` resets the selected step and every later step to `pending`, preserving successful earlier steps. This prevents stale downstream results after a middle step is retried.

Manually set a step status:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --set-step-status PLAN_ID S2 pending
```

Skip a step:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --skip-step PLAN_ID S3
```

Valid step statuses are:

```text
pending, running, success, failed, skipped, cancelled
```

## Execute After Approval

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --execute-plan "Read README.md and change Project status from TODO to READY"
```

This still is not full DAG execution. It is a conservative bridge from Plan Preview to Plan-and-Execute: the plan is approved by the user, then each plan step is handed to the ReAct executor serially.

Before execution, PyAgentCLI checks the local SQLite search index if one exists. If indexed files changed, disappeared, or new indexable files appeared, the approval text includes an index freshness warning and suggests running `pyagent --index`. PyAgentCLI does not silently rebuild the index during execution.

Plan steps now carry lightweight status:

```text
pending -> running -> success
pending -> cancelled
pending -> failed
```

In the current implementation, each step is delegated to the ReAct executor one at a time. The executor updates step status after each step, stops on the first failed step, and keeps tool-level approval for writes and shell commands.

Step-level approval:

- `READ` steps are allowed automatically.
- `WRITE`, `EXECUTE`, `NETWORK`, and `CRITICAL` steps ask for approval before execution.
- If a step is denied, it is marked `skipped`.
- Tool-level approval still applies inside the step, so a WRITE step can ask once at the plan level and again when `edit_file` or `write_file` is called.

Example output:

```text
PlanRun status: planned

Plan: Plan for: Read README.md and change Project status from TODO to READY

S1. [pending] Inspect workspace
   Risk: READ
   Tools: list_files, read_file
   List files and read the most relevant files before making changes.
S2. [pending] Apply minimal change
   Risk: WRITE
   Tools: edit_file, write_file
   Use edit_file for localized edits or write_file only for new files.
S3. [pending] Verify result
   Risk: EXECUTE
   Tools: run_shell
   Run a focused command or test if the user approves shell execution.
```

## Design Direction

The next stages are:

1. Let the user edit the plan before execution.
2. Add dependencies and turn the plan into a DAG.
3. Add explicit step retry controls.
4. Assign steps to Planner / Executor / Reviewer agents.
