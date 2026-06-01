# Developer Setup

PyAgentCLI requires Python 3.11 or newer.

## Recommended Setup

Create a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If your system `python3` is older than 3.11, install a newer Python first. PyAgentCLI uses modern Python features such as `StrEnum`.

## Run The CLI

```bash
PYTHONPATH=src python -m pyagentcli --help
```

Or, after editable install:

```bash
pyagent --help
```

## Optional Real Model Configuration

Without an API key, PyAgentCLI runs in local fallback mode.

For real model calls:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export PYAGENT_MODEL="gpt-4.1-mini"
```

You can also place these values in a workspace `.env` file.

## Generated Local State

PyAgentCLI writes local runtime state under `.pyagent/`:

- audit logs
- plan runs
- search index
- memory
- reviews
- eval reports

This directory is ignored by git.
