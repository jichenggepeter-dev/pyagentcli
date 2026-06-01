# Demo Script

This script shows the core PyAgentCLI workflow.

Use a Python 3.11+ environment. If installed in editable mode, replace `PYTHONPATH=src python -m pyagentcli` with `pyagent`.

## 1. Show CLI Surface

```bash
PYTHONPATH=src python -m pyagentcli --help
```

Point out:

- tool-calling task mode
- plan execution
- index
- memory
- eval

## 2. Build Code Index

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --index
```

Expected:

```text
Indexed 2 files into 2 chunks; skipped 0 files.
```

## 3. Use Symbol Context

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Explain @project_status"
```

With no API key, local fallback may not answer deeply, but `@project_status` is expanded through the context injection path. For a direct check:

```bash
PYTHONPATH=src python -c "from pyagentcli.cli.main import enrich_goal; print(enrich_goal('Explain @project_status', workspace='examples/demo_workspace'))"
```

Expected context contains:

```text
app.py:1-2 function project_status
```

## 4. Add Project Memory

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --remember "Prefer edit_file for localized changes."
```

Then inspect:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --memory
```

## 5. Preview A Plan

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --plan "Read README.md and change Project status from TODO to READY"
```

Point out:

- plan id
- step risks
- suggested tools
- persisted plan under `.pyagent/plans/`

## 6. Show Eval Harness

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval
```

Expected:

```text
Eval summary: 4/4 passed (100%); 0 failed.
```

Point out:

- deterministic evals validate the platform
- report is stored in `.pyagent/evals/`

## 7. Real Model Demo

After setting an OpenAI-compatible API key:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
```

Run:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Read README.md, then use edit_file to change Project status from TODO to READY. Do not use write_file."
```

Expected behavior:

- model calls `read_file`
- model calls `edit_file`
- write approval appears with diff preview
- audit log is written
- session memory is recorded

## 8. Close With Architecture

Summarize the project as:

```text
LLM + typed tools + safety + RAG + memory + planning + review + evals
```

The value is not only that the agent can edit files. The value is that every action is structured, reviewable, and measurable.
