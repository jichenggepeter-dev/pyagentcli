# PyAgentCLI

PyAgentCLI is a local Python AI coding agent CLI inspired by Claude Code, Codex CLI, and the PaiCLI Agent learning path.

It is not a plain chatbot wrapper. PyAgentCLI provides a local agent runtime around the model: typed tools, safety policy, code retrieval, memory, planning, review, and evals.

## Current Capabilities

- ReAct / tool-calling Agent Loop
- Filesystem tools: `list_files`, `read_file`, `write_file`, `edit_file`
- Shell tool: `run_shell`
- Search tools: `search_files`, `search_text`, `search_index`
- Safety: path guardrails, dangerous command denial, approval, audit log
- Plan-and-Execute: preview, approval, resume, retry, step status tracking
- RAG Lite: SQLite FTS, Python AST symbol chunks, `@file`, `@folder`, `@symbol`
- Memory: project notes and session summaries under `.pyagent/memory/`
- Reviewer: deterministic post-plan review with risk notes and suggested tests
- Eval Harness: deterministic local evals with JSONL reports

## Architecture

```text
CLI / REPL
  -> context enrichment
    -> RAG references: @file / @folder / @symbol
    -> project memory
  -> Agent Loop
    -> LLM Client
    -> Tool Registry
      -> Safety Policy
      -> Human Approval
      -> Audit Log
  -> Plan Executor
  -> Reviewer
  -> Eval Harness
```

The model never mutates the workspace directly. It emits tool calls, and PyAgentCLI validates, approves, executes, and audits those calls locally.

## Documentation

- [Roadmap](docs/roadmap.md)
- [Demo Script](docs/demo_script.md)
- [Developer Setup](docs/dev_setup.md)
- [Testing](docs/testing.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Interview Guide](docs/interview_guide.md)
- [Resume Bullets](docs/resume_bullets.md)
- [Plan Preview](docs/plan_preview.md)
- [RAG Lite](docs/rag_lite.md)
- [Memory](docs/memory.md)
- [Reviewer](docs/reviewer.md)
- [Eval Harness](docs/evals.md)
- [Real Model Demo](docs/e2e_real_model_demo.md)

## Quick Start

```bash
python -m pip install -e ".[dev]"
PYTHONPATH=src python -m pyagentcli --help
PYTHONPATH=src python -m pyagentcli "summarize this workspace"
PYTHONPATH=src python -m pyagentcli --index
PYTHONPATH=src python -m pyagentcli --plan "fix failing tests"
PYTHONPATH=src python -m pyagentcli --execute-plan "fix failing tests"
PYTHONPATH=src python -m pyagentcli --list-plans
PYTHONPATH=src python -m pyagentcli --show-plan PLAN_ID
PYTHONPATH=src python -m pyagentcli --resume-plan PLAN_ID
PYTHONPATH=src python -m pyagentcli --retry-step PLAN_ID STEP_ID
PYTHONPATH=src python -m pyagentcli --set-step-status PLAN_ID STEP_ID STATUS
PYTHONPATH=src python -m pyagentcli --skip-step PLAN_ID STEP_ID
PYTHONPATH=src python -m pyagentcli --remember "Prefer edit_file for small edits."
PYTHONPATH=src python -m pyagentcli --memory
PYTHONPATH=src python -m pyagentcli --eval
PYTHONPATH=src python -m pyagentcli
```

Run the local demo:

```bash
./scripts/demo.sh
```

For real model calls, set:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
```

You can also put those values in a workspace `.env` file. Shell environment variables win over `.env` values.

Without an API key, PyAgentCLI runs in local fallback mode so the CLI and tools can still be tested.

Use `--no-input` for non-interactive runs. In that mode, read-only tools can run, while write and shell tools are denied unless a future policy explicitly allows them.

## Model Check

After configuring an API key, verify that the model returns tool calls:

```bash
PYTHONPATH=src python -m pyagentcli --check-model
```

Expected output:

```text
tool_call: list_files args={'path': '.'}
```

For a full real-model walkthrough, see [docs/e2e_real_model_demo.md](docs/e2e_real_model_demo.md).

## Plan Preview

Preview a plan without executing tools:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --plan "Read README.md and change Project status from TODO to READY"
```

This follows the PaiCLI Plan-and-Execute direction: separate planning from execution first, then later upgrade plans into DAG execution.

Plans are persisted under `.pyagent/plans/*.json`. The CLI output includes a `Plan id`.

Show a persisted plan:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --show-plan PLAN_ID
```

List persisted plans:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --list-plans
```

Resume a persisted `planned` or `failed` plan:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --resume-plan PLAN_ID
```

Retry a specific step and all following steps:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --retry-step PLAN_ID S2
```

Manually edit step state:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --set-step-status PLAN_ID S2 pending

PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --skip-step PLAN_ID S3
```

To preview, approve, and then execute:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --execute-plan "Read README.md and change Project status from TODO to READY"
```

`--execute-plan` prints the plan first. If a local search index exists and may be stale, the approval text includes a freshness warning before execution. If you approve, PyAgentCLI passes the approved plan to the executor agent. Tool-level safety still applies, so `edit_file` and `run_shell` can still ask for approval before taking action.

After planned execution, PyAgentCLI runs a deterministic Reviewer and stores the result in the plan plus `.pyagent/reviews/PLAN_ID.md`. See [docs/reviewer.md](docs/reviewer.md).

## Eval Harness

Run built-in local evals:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval
```

Eval reports are written to `.pyagent/evals/*.jsonl`. See [docs/evals.md](docs/evals.md).

## Safety Preview

`write_file` and `edit_file` request approval before writing and show a unified diff preview. `edit_file` only replaces a unique `old_text` match; if the text is missing or appears multiple times, the edit is refused. `run_shell` also requests approval before execution.

## Demo Workspace

The repository includes a tiny workspace for end-to-end testing:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Read README.md, then use edit_file to change Project status from TODO to READY. Do not use write_file."
```

This should trigger a read tool call, an `edit_file` tool call, a diff approval prompt, an audit log entry, and a final model response.

## Memory

PyAgentCLI stores explicit local memory under `.pyagent/memory/`.

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --remember "Prefer edit_file for localized edits."

PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --memory
```

Project memory is injected into future tasks as context. Task runs and plan executions also write session summaries. See [docs/memory.md](docs/memory.md).

## RAG Lite

PyAgentCLI includes a first local retrieval tool:

```text
search_files(query, path=".", max_results=20, case_sensitive=false)
search_text(query, path=".", max_results=20, case_sensitive=false)
search_index(query, max_results=20)
```

`search_files` finds candidate files by path/name. `search_text` searches file contents and returns `path:line:snippet` matches. `search_index` queries the chunked SQLite FTS index created by `--index`, includes Python symbol labels when available, and warns when the index may be stale. See [docs/rag_lite.md](docs/rag_lite.md).

You can also reference explicit context in a task:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Summarize @README.md"
```

After building the index, symbol references can inject matching code chunks:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Explain @project_status"
```
