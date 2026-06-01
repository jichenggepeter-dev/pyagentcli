# Eval Harness v0.1

Eval Harness v0.1 gives PyAgentCLI a repeatable local evaluation loop.

It does not require a real model yet. The first cases check deterministic product capabilities:

- tool registry exposes core tools
- dangerous shell command is denied
- Python symbol search works
- project memory can persist notes

## Usage

```bash
PYTHONPATH=src python -m pyagentcli \
  --workspace examples/demo_workspace \
  --eval
```

The CLI prints a pass/fail summary and writes a JSONL report:

```text
.pyagent/evals/eval_YYYYMMDD_HHMMSS.jsonl
```

## Why Start Deterministic

Agent evaluation should separate platform regressions from model behavior. These cases verify that the local substrate works before testing LLM task success.

## Next Steps

1. Add model-backed task cases with expected file diffs.
2. Score tool-call correctness.
3. Score safety behavior such as denied commands and approval gates.
4. Feed Reviewer output into eval scoring.
