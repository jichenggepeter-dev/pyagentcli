#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "No Python executable found. Set PYTHON_BIN=/path/to/python." >&2
    exit 1
  fi
fi

export PYTHONPATH="${PYTHONPATH:-src}"

echo "== PyAgentCLI help =="
"$PYTHON_BIN" -m pyagentcli --help

echo
echo "== Build demo workspace index =="
"$PYTHON_BIN" -m pyagentcli --workspace examples/demo_workspace --index

echo
echo "== Symbol context injection =="
"$PYTHON_BIN" -c "from pyagentcli.cli.main import enrich_goal; print(enrich_goal('Explain @project_status', workspace='examples/demo_workspace'))"

echo
echo "== Project memory =="
"$PYTHON_BIN" -m pyagentcli --workspace examples/demo_workspace --remember "Prefer edit_file for localized changes."
"$PYTHON_BIN" -m pyagentcli --workspace examples/demo_workspace --memory

echo
echo "== Plan preview =="
"$PYTHON_BIN" -m pyagentcli --workspace examples/demo_workspace --plan "Read README.md and change Project status from TODO to READY"

echo
echo "== Built-in evals =="
"$PYTHON_BIN" -m pyagentcli --workspace examples/demo_workspace --eval
