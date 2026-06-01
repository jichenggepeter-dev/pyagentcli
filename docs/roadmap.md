# PyAgentCLI Roadmap

This roadmap captures the current closeout state of PyAgentCLI.

PyAgentCLI is a local Python AI Coding Agent CLI inspired by Claude Code, Codex CLI, and the PaiCLI Agent learning path. The project now has a working core loop and several production-shaped subsystems.

## Completed Core

### Agent Loop

- ReAct / tool-calling loop
- OpenAI-compatible LLM client
- local fallback mode when no API key is configured
- max-step guardrail
- CLI and REPL entry points

### Tools

- `list_files`
- `read_file`
- `write_file`
- `edit_file`
- `run_shell`
- `search_files`
- `search_text`
- `search_index`

### Safety

- path guardrails
- command deny policy
- tool risk levels
- human approval for write and shell actions
- JSONL audit log

### Plan-and-Execute

- `--plan`
- `--execute-plan`
- `--list-plans`
- `--show-plan`
- `--resume-plan`
- `--retry-step`
- `--set-step-status`
- `--skip-step`
- persisted plans under `.pyagent/plans/`
- step status tracking
- plan execution freshness warning when search index may be stale

### RAG Lite

- deterministic file and text search
- SQLite FTS index
- line-window chunks
- Python AST symbol chunks for functions, classes, and methods
- exact `@symbol` lookup with fallback to FTS
- `@file`, `@folder`, and `@symbol` context injection
- stale-index warning

### Memory

- `--remember`
- `--memory`
- project memory under `.pyagent/memory/project.md`
- session summaries under `.pyagent/memory/sessions/`
- project memory injection before task execution

### Reviewer

- deterministic Reviewer after planned execution
- review result persisted into plan JSON
- Markdown review artifact under `.pyagent/reviews/`
- risk notes and suggested tests

### Eval Harness

- `--eval`
- deterministic platform evals
- JSONL reports under `.pyagent/evals/`
- initial cases for tool registry, safety, RAG, and memory

## Not Yet Built

### MCP v0.1

- MCP client
- MCP tool adapter
- remote tool risk classification
- MCP audit integration

### Browser Tools

- Playwright-backed browser tool
- screenshot and DOM inspection
- local frontend verification flows

### Multi-Agent v0.2

- model-separated Planner / Executor / Reviewer
- message contract between agents
- reviewer gate before marking plan complete

### Advanced RAG

- embeddings
- hybrid retrieval
- import graph or dependency graph
- multi-language symbol chunking

### Advanced Memory

- memory compressor
- stale memory detection
- user-level memory
- memory review and deletion commands

### Skill System

- local skill loader
- skill metadata
- skill selection and injection

### Model-Backed Eval

- task fixtures with expected file diffs
- tool-call accuracy scoring
- task success rate
- safety violation rate

## Recommended Next Phases

1. **Project polish**
   Make installation and testing smooth, clean generated files, and add a reproducible demo script.

2. **MCP v0.1**
   Add a minimal MCP client and expose MCP tools through the existing ToolRegistry.

3. **Browser v0.1**
   Add Playwright tools for local UI inspection and verification.

4. **Model-backed Eval v0.2**
   Add fixture workspaces and expected outcomes for real coding tasks.

5. **Advanced Multi-Agent**
   Split Planner, Executor, and Reviewer into separate agent roles with explicit contracts.
