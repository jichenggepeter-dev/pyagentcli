# PyAgentCLI Roadmap

This roadmap captures the current closeout state of PyAgentCLI.

PyAgentCLI is a local Python AI Coding Agent CLI inspired by Claude Code, Codex CLI, and the PaiCLI Agent learning path. The project now has a working core loop and several production-shaped subsystems.

For the detailed phase-by-phase execution plan, see [execution_plan_zh.md](execution_plan_zh.md).

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
- `inspect_page`

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
- hybrid retrieval interface
- optional embedding provider interface with disabled-by-default fallback
- optional SQLite vector store for chunk embeddings
- hybrid FTS/vector result deduping
- configurable hash and OpenAI-compatible embedding providers
- embedding failure fallback to FTS
- Python import graph extraction
- import dependency query API

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
- Reviewer gate prevents skipped, failed, or cancelled steps from being marked successful

### Eval Harness

- `--eval`
- deterministic platform evals
- JSONL reports under `.pyagent/evals/`
- initial cases for tool registry, safety, RAG, and memory
- coding task eval fixture with expected file outcome
- task success rate, tool-call accuracy, and safety violation metrics

### MCP v0.1

- minimal stdio MCP client
- JSON-RPC initialize/list/call flow
- MCP tool adapter for the existing `ToolRegistry`
- project-level `pyagent.toml` MCP server config
- automatic MCP tool registration during Agent startup
- read-only MCP tool support via `readOnlyHint`
- non-read MCP tools classified as `NETWORK` or `CRITICAL` and denied by default policy

### Browser v0.1

- local page inspection tool
- workspace-relative HTML and workspace `file://` support
- localhost, 127.0.0.1, and ::1 URL support
- external URL denial by default
- title and normalized text snapshot extraction

### Multi-Agent v0.2

- explicit Planner / Executor / Reviewer role contracts
- `ExecutorStepContract` for step-level execution
- `ReviewerGateDecision` for final plan status gating
- Reviewer gate can downgrade a successful execution to failed when steps were skipped, failed, or cancelled

## Not Yet Built

### Advanced Browser Tools

- Playwright-backed screenshots and DOM inspection
- console and network logs
- local frontend interaction flows

### Advanced RAG

- dependency-aware retrieval output or tool
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

## Recommended Next Phases

1. **Advanced RAG dependency tool**
   Expose import graph queries through a safe read-only tool or retrieval context.

2. **Advanced Multi-Agent**
   Split Planner, Executor, and Reviewer into separate model-backed role clients and add retry handoff.

3. **Advanced Browser tools**
   Add Playwright-backed screenshots, DOM inspection, console logs, and local UI interaction.

4. **Model-backed Eval v0.3**
   Replace simulated tool calls with captured Agent runs and expected diff scoring.
