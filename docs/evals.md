# Eval Harness v0.2

Eval Harness gives PyAgentCLI a repeatable local evaluation loop.

It has two layers:

- platform evals
- coding task evals
- RAG retrieval evals

Neither layer requires a real model yet. This keeps the scorer deterministic before model-backed execution is added.

## Platform Evals

Platform evals check deterministic product capabilities:

- tool registry exposes core tools
- dangerous shell command is denied
- Python symbol search works
- project memory can persist notes

## Coding Task Evals

Coding task evals use fixture workspaces, expected file outcomes, expected tool calls, and forbidden tool checks.

The first task:

- starts with `README.md` containing `Project status: TODO`
- replays the expected `read_file` and `edit_file` tool calls
- verifies the file contains `Project status: READY`
- checks that forbidden tools such as `run_shell` were not used

The reported metrics are:

- task success rate
- tool-call accuracy
- safety violation count

## RAG Retrieval Evals

RAG retrieval evals check whether the retrieval layer returns the expected context:

- Python symbol lookup
- TypeScript symbol lookup
- dependency context injection

These evals do not call a model. They build fixture workspaces, rebuild the local index, and check deterministic retrieval output.

## Usage

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval
```

The CLI prints platform and coding-task summaries and writes a JSONL report:

```text
.pyagent/evals/eval_YYYYMMDD_HHMMSS.jsonl
```

Report lines include a `kind` field:

```json
{"kind": "platform", "case_id": "tools.registry", "...": "..."}
{"kind": "coding_task", "case_id": "coding.update_readme_status", "...": "..."}
{"kind": "rag_retrieval", "case_id": "rag_retrieval.typescript_symbol", "...": "..."}
```

## Why Start Deterministic

Agent evaluation should separate platform regressions from model behavior. These cases verify that the local substrate works before testing LLM task success.

## Next Steps

1. Replace simulated tool calls with captured Agent runs.
2. Add expected diff scoring, not only expected text containment.
3. Feed Reviewer output into eval scoring.
4. Add per-model and per-retriever comparison reports.
