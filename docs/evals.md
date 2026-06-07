# Eval Harness v0.4

Eval Harness gives PyAgentCLI a repeatable local evaluation loop.

It has two layers:

- platform evals
- coding task evals
- RAG retrieval evals
- captured trace evals
- Reviewer output evals
- opt-in real model trace evals

The default layers do not require a real model. This keeps the scorer deterministic and dependency-light. Real model trace capture is available only through an explicit opt-in flag.

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
- diff accuracy
- safety violation count

## RAG Retrieval Evals

RAG retrieval evals check whether the retrieval layer returns the expected context:

- Python symbol lookup
- TypeScript symbol lookup
- dependency context injection

These evals do not call a model. They build fixture workspaces, rebuild the local index, and check deterministic retrieval output.

## Captured Trace Evals

Trace evals score an auditable Agent-like run trace:

- user goal
- assistant tool calls
- tool observations
- final assistant output

The first trace eval checks:

- expected tool sequence
- forbidden tool usage
- final output containment

Coding task evals also score expected file diffs. The first case verifies that the actual unified diff removes `Project status: TODO` and adds `Project status: READY`.

This creates the scoring contract for future real Agent runs. Once the Agent loop can emit captured traces, those traces can be scored with the same metrics.

PyAgentCLI also includes a local fallback Agent trace eval. It runs the real `AgentLoop`, captures tool calls and observations, and scores the resulting trace without requiring an API key.

## Real Model Trace Evals

Real model trace evals run the real `AgentLoop` with the configured OpenAI-compatible model and capture the emitted tool trace.

They are disabled by default. This prevents `pyagent --eval` from making external API calls.

Enable them explicitly:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval \
  --eval-real-model
```

If `OPENAI_API_KEY` is not configured, the CLI prints a disabled message instead of falling back to the local model.

The first real model trace case checks:

- expected `list_files` tool use
- forbidden write, shell, and browser interaction tools
- final output containing `README.md`

## Reviewer Output Evals

Reviewer evals score the deterministic Reviewer after plan execution.

The built-in fixtures cover:

- a successful plan that should pass the Reviewer gate
- a failed step that should be blocked with a `retry_step` proposal
- a skipped step that should be blocked with a `user_decision` proposal

The reported metrics are:

- gate match count
- proposal action match count
- suggested-tests match count

## Usage

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval
```

The CLI prints platform, coding-task, RAG, trace, Reviewer, and real-model trace summaries and writes a JSONL report:

```text
.pyagent/evals/eval_YYYYMMDD_HHMMSS.jsonl
```

Report lines include a `kind` field:

```json
{"kind": "platform", "case_id": "tools.registry", "...": "..."}
{"kind": "coding_task", "case_id": "coding.update_readme_status", "...": "..."}
{"kind": "rag_retrieval", "case_id": "rag_retrieval.typescript_symbol", "...": "..."}
{"kind": "trace_eval", "case_id": "trace.update_readme_status", "...": "..."}
{"kind": "reviewer_eval", "case_id": "reviewer.failed_step", "...": "..."}
{"kind": "real_model_trace_eval", "case_id": "real_model_trace.list_workspace", "...": "..."}
```

## Why Start Deterministic

Agent evaluation should separate platform regressions from model behavior. These cases verify that the local substrate works before testing LLM task success.

## Next Steps

1. Add per-model trace comparison reports.
2. Add Reviewer proposal comparison evals.
3. Add per-retriever comparison reports.
