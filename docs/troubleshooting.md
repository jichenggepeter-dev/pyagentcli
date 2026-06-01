# Troubleshooting

## `python: command not found`

Some macOS environments expose only `python3`.

Use:

```bash
PYTHONPATH=src python3 -m pyagentcli --help
```

If `python3` is older than 3.11, install a newer Python and create a virtual environment.

## `ImportError: cannot import name 'StrEnum'`

Your Python version is too old. `StrEnum` requires Python 3.11+.

Check:

```bash
python --version
```

Install Python 3.11 or newer.

## `No module named pytest`

Install dev dependencies:

```bash
python -m pip install -e ".[dev]"
```

Then run:

```bash
python -m pytest
```

If you cannot install dependencies, use smoke checks:

```bash
PYTHONPATH=src python -m compileall src tests
PYTHONPATH=src python -m pyagentcli --workspace examples/demo_workspace --eval
```

## No API Key Configured

This is expected for local development. PyAgentCLI will use `LocalFallbackClient`.

To use a real model, configure:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
```

## Search Index Seems Stale

Rebuild it:

```bash
PYTHONPATH=src python -m pyagentcli --workspace examples/demo_workspace --index
```

PyAgentCLI warns when indexed files change after indexing.

## GitHub Push

This workspace may start without a git repository. Initialize and commit locally first:

```bash
git init
git add .
git commit -m "Initial PyAgentCLI project"
```

Then add a GitHub remote:

```bash
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin main
```
