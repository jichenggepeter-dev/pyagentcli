# Eval Harness v0.4

Eval Harness gives PyAgentCLI a repeatable local evaluation loop.

It has two layers:

- platform evals
- coding task evals
- RAG retrieval evals
- captured trace evals
- Reviewer output evals
- opt-in real model trace evals
- Reviewer proposal comparison evals

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

## Retriever Comparison Evals

Retriever comparison evals compare retrieval strategies on fixed local fixtures:

- `exact`: SQLite FTS search
- `vector-hash`: deterministic local hash embedding vector search
- `hybrid-hash`: merged exact and vector retrieval
- `vector-disabled`: disabled row proving the no-provider path is explicit

These evals do not call external embedding services. The vector-enabled comparison uses the deterministic `hash` provider so default evals remain local and repeatable.

The reported metrics are:

- enabled comparison pass rate
- disabled comparison count
- hit path, rank, and score per retriever

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

## Per-Model Trace Comparison

Per-model trace comparison runs the same real model trace cases across multiple explicitly configured model clients.

It is disabled by default. `pyagent --eval` does not call external APIs, even when model comparison config exists.

Enable comparison explicitly:

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval \
  --eval-compare-models
```

Configure comparison models in the workspace `pyagent.toml`:

```toml
[evals.model_comparison.models.fast]
model = "gpt-4.1-mini"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"

[evals.model_comparison.models.reasoning]
model = "gpt-4.1"
base_url = "https://api.openai.com/v1"
api_key_env = "REASONING_MODEL_API_KEY"
```

If no models are configured, or none of the configured API key environment variables are present, the CLI prints a disabled message instead of running comparison.

The reported metrics are:

- model count
- final output pass/fail per model and case
- tool-call accuracy
- safety violation count

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

## Reviewer Proposal Comparison Evals

Reviewer proposal comparison evals compare deterministic retry proposals with optional model-backed suggestions.

The built-in fixtures cover:

- model action matches deterministic `retry_step`
- model action mismatches by suggesting `accept`
- invalid model JSON downgrades to `inspect`

The reported metrics are:

- passed comparison fixtures
- model-action match rate
- mismatch count

## Usage

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval
```

The CLI prints platform, coding-task, RAG, retriever comparison, trace, Reviewer, real-model trace, per-model trace comparison, and Reviewer proposal comparison summaries and writes a JSONL report:

```text
.pyagent/evals/eval_YYYYMMDD_HHMMSS.jsonl
```

Report lines include a `kind` field:

```json
{"kind": "platform", "case_id": "tools.registry", "...": "..."}
{"kind": "coding_task", "case_id": "coding.update_readme_status", "...": "..."}
{"kind": "rag_retrieval", "case_id": "rag_retrieval.typescript_symbol", "...": "..."}
{"kind": "retriever_comparison", "retriever_name": "hybrid-hash", "case_id": "retriever_compare.project_status", "...": "..."}
{"kind": "trace_eval", "case_id": "trace.update_readme_status", "...": "..."}
{"kind": "reviewer_eval", "case_id": "reviewer.failed_step", "...": "..."}
{"kind": "real_model_trace_eval", "case_id": "real_model_trace.list_workspace", "...": "..."}
{"kind": "model_trace_comparison", "model_name": "fast", "case_id": "real_model_trace.list_workspace", "...": "..."}
{"kind": "reviewer_proposal_comparison", "case_id": "reviewer_proposal_compare.matched_retry", "...": "..."}
```

## Why Start Deterministic

Agent evaluation should separate platform regressions from model behavior. These cases verify that the local substrate works before testing LLM task success.

## Next Steps

1. Add changed-file risk scoring to Reviewer.
2. Add browser assertion evals.
3. Add richer dependency context such as imported-by edges.
