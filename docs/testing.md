# Testing

## Full Test Suite

After installing dev dependencies:

```bash
python -m pytest
```

The test suite covers:

- agent loop
- CLI parsing and workflows
- safety policy
- filesystem and shell tools
- RAG chunking and indexing
- context injection
- plan execution
- memory
- reviewer
- eval harness

## No-Pytest Smoke Checks

If `pytest` is not installed, run these smoke checks:

```bash
PYTHONPATH=src python -m compileall src tests
PYTHONPATH=src python -m pyagentcli --help
PYTHONPATH=src python -m pyagentcli --workspace examples/demo_workspace --eval
```

Expected eval output:

```text
Eval summary: 4/4 passed (100%); 0 failed.
```

## Demo Script

The scripted local demo runs the same core checks:

```bash
./scripts/demo.sh
```

The script uses `PYTHON_BIN` if provided:

```bash
PYTHON_BIN=/path/to/python ./scripts/demo.sh
```

## Real Model Testing

Model-backed behavior requires API configuration:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
```

Then run:

```bash
PYTHONPATH=src python -m pyagentcli --check-model
```

This verifies that the configured model can return tool calls.
