# PyAgentCLI Real Model E2E Demo

This demo verifies the PaiCLI-style first-stage loop in PyAgentCLI:

```text
User task
  -> LLM decides to call tools
  -> PyAgentCLI executes local tools
  -> write/edit tool shows diff preview
  -> user approves
  -> tool result returns to the LLM
  -> final answer is produced
```

## 1. Configure Model

Use environment variables:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
```

Or create `examples/demo_workspace/.env` with the same values. Do not commit real keys.

## 2. Check Tool Calling

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --check-model
```

Expected:

```text
tool_call: list_files args={'path': '.'}
```

If the model answers directly instead of returning a tool call, use a model with stronger function/tool calling support.

## 3. Run The ReAct + Tool Call Demo

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Read README.md, then use edit_file to change Project status from TODO to READY. Do not use write_file."
```

Expected sequence:

1. The model calls `read_file` or `list_files`.
2. The model calls `edit_file`.
3. PyAgentCLI shows a unified diff preview.
4. You approve the edit.
5. The model receives the tool result and summarizes the change.

Expected diff:

```diff
-Project status: TODO
+Project status: READY
```

## 4. Check The File

```bash
cat examples/demo_workspace/README.md
```

Expected:

```text
Project status: READY
```

## 5. Check Audit Log

```bash
tail -n 5 examples/demo_workspace/.pyagent/audit.log.jsonl
```

You should see records for read/edit tool calls, including approval decisions and result status.

## Reset Demo Workspace

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  "Use edit_file to change Project status from READY back to TODO in README.md."
```

