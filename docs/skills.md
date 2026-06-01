# Skill System

PyAgentCLI skills are local, prompt-only guidance files. They help the Agent adopt project-specific workflows without turning guidance into executable plugins.

## What Skills Do

- load metadata from `.pyagent/skills/<skill>/skill.toml`
- load guidance text from `.pyagent/skills/<skill>/SKILL.md`
- select skills by keyword trigger in the user task
- inject selected guidance into the Agent goal
- list enabled skills with `--list-skills`

Skills do not execute tools, bypass approvals, or override safety policy. They are context, not authority.

## Directory Format

```text
.pyagent/
  skills/
    python-testing/
      skill.toml
      SKILL.md
```

Example `skill.toml`:

```toml
name = "python-testing"
description = "Guidance for Python test workflows."
triggers = ["pytest", "test", "testing"]
enabled = true
```

Example `SKILL.md`:

```markdown
Prefer focused pytest runs before full test runs.
When a bug touches one module, run that module's tests first.
Mention any tests that were not run.
```

## CLI

List enabled local skills:

```bash
PYTHONPATH=src python -m pyagentcli --list-skills
```

Run a task that can trigger a skill:

```bash
PYTHONPATH=src python -m pyagentcli "run pytest for the edited module"
```

If the task contains a trigger such as `pytest`, PyAgentCLI appends the matched skill guidance to the enriched task context.

## Design Boundary

The Skill System is intentionally smaller than MCP:

- use a skill for local behavior guidance, conventions, or checklists
- use MCP when the Agent needs a new external tool
- use memory when the user explicitly wants PyAgentCLI to remember a project preference
- use RAG when the Agent needs code context from the repository

This keeps skills safe and predictable while still giving the Agent reusable project knowledge.
