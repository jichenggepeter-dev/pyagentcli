# PyAgentCLI Agent Guide

This file is the project handoff guide for future coding-agent sessions.

## Product Intent

PyAgentCLI is a local Python AI coding agent CLI for developers. It is inspired by Claude Code, Codex CLI, and the PaiCLI Agent learning path, but it is an original Python implementation.

The product goal is to make a small but real coding agent runtime:

- ReAct and tool-calling loop
- local file, shell, and search tools
- safety policy, human approval, and audit logs
- RAG context injection
- memory
- plan execution
- reviewer
- eval harness
- MCP and browser extensions
- later multi-agent collaboration

## Architecture Rules

- Runtime language: Python 3.11+.
- Source code lives under `src/pyagentcli/`.
- Tests live under `tests/`.
- User-facing docs live under `docs/`.
- Generated runtime state belongs under `.pyagent/` and must stay ignored.
- The model must never mutate the workspace directly; it must call tools.
- Tool execution must flow through `ToolRegistry`, `SafetyPolicy`, `ApprovalHandler`, and `AuditLogger`.
- New risky capabilities should default to denied or approval-gated.
- Prefer deterministic local tests before adding model-dependent behavior.

## Current Phase

Phase 2 has started.

Completed:

- Phase 1 core agent runtime
- MCP v0.1 client and adapter

Next recommended slice:

- MCP config and CLI integration

## Operating Rules

- Before each non-trivial change, define the phase slice and edit scope.
- Keep each change small enough to test in isolation.
- Add or update tests before claiming a feature is complete.
- Update docs when the user-facing behavior or architecture changes.
- Run targeted tests first, then the full suite before final handoff.
- Do not introduce new dependencies unless the phase requires them and the reason is documented.
- Do not widen scope silently; create a new phase slice instead.

## Default Verification

Use these checks unless a narrower phase document says otherwise:

```bash
.venv/bin/python -m pytest
```

For CLI behavior:

```bash
PYTHONPATH=src .venv/bin/python -m pyagentcli --help
```

For demo validation:

```bash
PYTHON_BIN=.venv/bin/python ./scripts/demo.sh
```

## Edit Boundaries By Area

Agent loop:

- `src/pyagentcli/agent/**`
- `tests/test_agent_loop.py`
- `tests/test_plan_executor.py`
- related docs

Tools and safety:

- `src/pyagentcli/tools/**`
- `src/pyagentcli/safety/**`
- `tests/test_tools.py`
- `tests/test_safety_policy.py`

RAG:

- `src/pyagentcli/rag/**`
- `src/pyagentcli/context_injection.py`
- `tests/test_rag_*.py`
- `tests/test_context_injection.py`

Memory:

- `src/pyagentcli/memory/**`
- `tests/test_memory.py`
- `docs/memory.md`

MCP:

- `src/pyagentcli/mcp/**`
- config and CLI files only when the current slice explicitly requires integration
- `tests/test_mcp.py`
- `docs/mcp.md`

Browser:

- `src/pyagentcli/tools/browser.py` or `src/pyagentcli/browser/**`
- browser-specific tests
- browser docs

Evals:

- `src/pyagentcli/evals/**`
- `tests/test_evals.py`
- eval fixtures
- `docs/evals.md`

