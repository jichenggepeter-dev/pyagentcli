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
- `search_dependencies` read-only dependency tool
- dependency context injection for `@file` and `@symbol`
- JavaScript and TypeScript symbol chunking for common functions, classes, and arrow functions

### Memory

- `--remember`
- `--memory`
- `--compress-memory`
- `--delete-memory-line`
- `--stale-memory-days`
- project memory under `.pyagent/memory/project.md`
- session summaries under `.pyagent/memory/sessions/`
- project memory injection before task execution
- deterministic session compression
- explicit memory deletion
- stale memory reporting

### Skill System v0.1

- local skill loader under `.pyagent/skills/`
- `skill.toml` metadata and `SKILL.md` guidance files
- trigger-based skill selection
- bounded prompt injection
- `--list-skills`
- skills treated as guidance that cannot override user tasks, safety policy, or approvals

### Reviewer

- deterministic Reviewer after planned execution
- review result persisted into plan JSON
- Markdown review artifact under `.pyagent/reviews/`
- risk notes and suggested tests
- Reviewer gate prevents skipped, failed, or cancelled steps from being marked successful
- optional model-backed Reviewer suggestions when reviewer role config and API key are present
- model suggestions are advisory and cannot override the deterministic gate

### Eval Harness

- `--eval`
- deterministic platform evals
- JSONL reports under `.pyagent/evals/`
- initial cases for tool registry, safety, RAG, and memory
- coding task eval fixture with expected file outcome
- task success rate, tool-call accuracy, and safety violation metrics
- RAG retrieval evals for Python symbols, TypeScript symbols, and dependency context
- captured trace eval with expected tool sequence, forbidden tool checks, and final output scoring
- AgentLoop trace capture with local fallback trace eval
- expected diff scoring for coding task evals
- Reviewer output scoring for gate decisions, retry proposals, and suggested tests

### Release and Packaging v0.1

- `pyagent` console script declared in `pyproject.toml`
- package metadata smoke tests
- CI CLI smoke checks after editable install
- release checklist for tag, docs, tests, and known limitations

### MCP v0.1

- minimal stdio MCP client
- JSON-RPC initialize/list/call flow
- MCP tool adapter for the existing `ToolRegistry`
- project-level `pyagent.toml` MCP server config
- automatic MCP tool registration during Agent startup
- read-only MCP tool support via `readOnlyHint`
- non-read MCP tools classified as `NETWORK` or `CRITICAL` and denied by default policy

### Browser v0.2

- local page inspection tool
- workspace-relative HTML and workspace `file://` support
- localhost, 127.0.0.1, and ::1 URL support
- external URL denial by default
- title and normalized text snapshot extraction
- DOM-oriented static snapshot tool
- optional Playwright console log and screenshot tool shells with clear missing-dependency fallback
- screenshot output restricted to `.pyagent/browser/`
- `--check-browser` optional capability diagnostic
- `browser` optional dependency extra for Playwright
- read-only `browser_query_selector` for simple tag, id, and class selectors

### Multi-Agent v0.3

- explicit Planner / Executor / Reviewer role contracts
- `ExecutorStepContract` for step-level execution
- `ReviewerGateDecision` for final plan status gating
- Reviewer gate can downgrade a successful execution to failed when steps were skipped, failed, or cancelled
- persisted agent handoffs for Planner, Executor, and Reviewer
- Reviewer handoff recommendations for accept, retry, resume, or user decision
- role-level model and prompt config for Planner, Executor, and Reviewer
- read-only Reviewer retry proposals for failed, skipped, or cancelled steps
- optional model-backed Reviewer suggestions alongside deterministic retry proposals

## Not Yet Built

### Advanced Browser Tools

- Playwright install/setup workflow
- interactive local frontend flows
- network logs
- local frontend interaction flows

### Advanced RAG

- richer dependency context such as imported-by edges
- retriever comparison metrics

### Advanced Memory

- memory compressor
- stale memory detection
- user-level memory
- memory review and deletion commands

## Recommended Next Phases

1. **Advanced Browser Interaction**
   Add user-approved local click/type flows after selector query is stable.

2. **Real Model Trace Capture**
   Capture and score real model tool-call traces behind explicit API configuration.

3. **Reviewer Proposal Comparison Eval**
   Compare deterministic Reviewer proposals against optional model-backed suggestions.
