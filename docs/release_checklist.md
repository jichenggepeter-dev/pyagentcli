# Release Checklist

Use this checklist before tagging a PyAgentCLI release.

## 1. Metadata

- Confirm `pyproject.toml` has the intended `project.name`.
- Confirm `project.version` matches the release tag.
- Confirm `requires-python` matches the supported Python versions.
- Confirm the `pyagent` console script points to `pyagentcli.cli.main:main`.

## 2. Local Verification

```bash
python -m pip install -e ".[dev]"
python -m pytest
pyagent --help
pyagent --workspace examples/demo_workspace --index
pyagent --workspace examples/demo_workspace --eval
```

Expected eval headline:

```text
Eval summary: 4/4 passed (100%); 0 failed.
```

## 3. Documentation

- README quick start uses commands that work after editable install.
- `docs/roadmap.md` reflects the released capability set.
- `docs/execution_plan_zh.md` points to the next execution card.
- Any new CLI flag has a docs page or README mention.

## 4. GitHub Release

- Ensure `main` is green in GitHub Actions.
- Create a tag matching `pyproject.toml`, for example `v0.1.0`.
- Include a short capability summary.
- Include test evidence from the local verification step.
- Mention known limitations and the next planned phase.

## 5. Known v0.1 Scope

- Local fallback works without an API key.
- Real model usage requires OpenAI-compatible environment variables.
- MCP is v0.1 and supports safe read-only adapter behavior first.
- Browser support is local inspection only; Playwright interaction is a later phase.
